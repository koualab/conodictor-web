#!/usr/bin/env python3

from Bio import SearchIO
from Bio.Seq import reverse_complement, translate
from collections import Counter, defaultdict
import csv
from datetime import datetime
from functools import reduce
import gzip
from heapq import nsmallest
from matplotlib import pyplot as plt
import numpy as np
from operator import mul
import os
import logging
import pandas as pd
import pathlib
import pyfastx
import re
import shutil
import subprocess
import sys
import warnings


def conodictor(infile, outdir, force=False, allres=False):

    # Functions -------------------------------------------------------------
    def donut_graph():
        """
        Make a donut graph from stats of predicted sequences.
        """
        data = pd.read_table(pathlib.Path(outdir, "summary.txt"))
        plot_data = data[data.columns[3]].tolist()
        dtc = Counter(plot_data)
        labels = [
            f"{k1}: {v1}"
            for k1, v1 in dtc.items()
            if not k1.startswith("CONFLICT")
        ]
        values = [x for k2, x in dtc.items() if not k2.startswith("CONFLICT")]

        # White circle
        _, ax = plt.subplots(figsize=(8, 5), subplot_kw=dict(aspect="equal"))
        wedges, _ = ax.pie(
            np.array(values).ravel(),
            wedgeprops=dict(width=0.5),
            startangle=-40,
        )

        bbox_props = dict(
            boxstyle="square,pad = 0.3", fc="w", ec="k", lw=0.72
        )

        kw = dict(
            arrowprops=dict(arrowstyle="-"),
            bbox=bbox_props,
            zorder=0,
            va="center",
        )

        for i, p in enumerate(wedges):
            ang = (p.theta2 - p.theta1) / 2.0 + p.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            connectionstyle = f"angle, angleA = 0, angleB = {ang}"
            kw["arrowprops"].update({"connectionstyle": connectionstyle})
            ax.annotate(
                labels[i],
                xy=(x, y),
                xytext=(1.35 * np.sign(x), 1.4 * y),
                horizontalalignment=horizontalalignment,
                **kw,
            )

        ax.set_title("ConoDictor Predictions")
        plt.savefig(
            pathlib.Path(outdir, "superfamilies_distribution.png"), dpi=300
        )

    def cdpred(hmmclass, pssmclass):
        """
        Gives definitive classification by combining HMM
        and PSSM classification.
        Arguments:
        - hmmclass  - HMM predicted family, required (string)
        - pssmclass - PSSM predicted family, required (string)

        """
        deffam = None

        if hmmclass == pssmclass:
            deffam = hmmclass
        elif "CONFLICT" in pssmclass and "CONFLICT" in hmmclass:
            fams_pssm = re.search("(?<=CONFLICT)(.*)and(.*)", pssmclass)
            fams_hmm = re.search("(?<=CONFLICT)(.*)and(.*)", hmmclass)
            deffam = f"CONFLICT {fams_pssm.group(1)}, {fams_pssm.group(2)},"
            +f" {fams_hmm.group(1)}, and {fams_hmm.group(2)}"
        elif "CONFLICT" in pssmclass and "CONFLICT" not in hmmclass:
            deffam = hmmclass
        elif "CONFLICT" in hmmclass and "CONFLICT" not in pssmclass:
            deffam = pssmclass
        elif pssmclass != hmmclass:
            deffam = f"CONFLICT {hmmclass} and {pssmclass}"

        return deffam

    def test_sequence(s):
        """
        Test sequence type
        """
        dna = "ATCG"
        prot = "ABCDEFGHIKLMNPQRSTVWXYZ"
        stype = ""

        if all(i in dna for i in s):
            stype = "DNA"
        elif all(i in prot for i in s):
            stype = "protein"
        else:
            stype = "unknown"

        return stype

    def get_pssm_fam(mdict):
        """
        Give predicted family by PSSM.

        Argument:
        - mdict - Dictionnary, required (dict)

        Return the family with the highest number of occurence in PSSM profile
        match recorded as list for each sequence id.

        >>> my_dict = {ID1: ['A', 'A', 'B', 'M'], ID2: ['M', 'P', 'O1', 'O1']}
        >>> get_pssm_fam(my_dict)
        {ID1: 'A', ID2: 'O1'}
        """
        fam = ""
        pssmfam = {}
        for key in mdict.keys():
            x = Counter(mdict[key])
            # Take the top 2 item with highest count in list
            possible_fam = x.most_common(2)

            if len(possible_fam) == 1:
                fam = possible_fam[0][0]
            elif len(possible_fam) > 1:
                if possible_fam[0][1] == possible_fam[1][1]:
                    fam = (
                        f"CONFLICT {possible_fam[0][0]}"
                        + f" and {possible_fam[1][0]}"
                    )
                elif possible_fam[0][1] > possible_fam[1][1]:
                    fam = possible_fam[0][0]
                else:
                    fam = possible_fam[1][0]

            pssmfam[key] = fam

        return pssmfam

    def hmm_threshold(mdict):
        """
        Calculate evalue by family for each sequence.

        Argument:
        - mdict: Dictionnary, required (dict)

        Return a dict with the evalue for each family.
        """
        score = defaultdict(dict)
        for key in mdict.keys():
            for k, v in mdict[key].items():
                score[key][k] = reduce(mul, v, 1)

        return score

    def get_hmm_fam(mdict):
        """
        Get sequence family from hmm dictionnary.
        """
        conofam = ""
        seqfam = {}
        for key in mdict.keys():
            two_smallest = nsmallest(2, mdict[key].values())

            if len(two_smallest) == 1:
                conofam = next(iter(mdict[key]))
            elif two_smallest[0] * 100 != two_smallest[1]:
                conofam = list(mdict[key].keys())[
                    list(mdict[key].values()).index(two_smallest[0])
                ]
            elif two_smallest[0] * 100 == two_smallest[1]:
                fam1 = list(mdict[key].keys())[
                    list(mdict[key].values()).index(two_smallest[0])
                ]
                fam2 = list(mdict[key].keys())[
                    list(mdict[key].values()).index(two_smallest[1])
                ]
                conofam = f"CONFLICT {fam1} and {fam2}"

            seqfam[key] = conofam

        return seqfam

    def msg(text):
        """
        Produce nice message and info output on terminal.
        """
        t = datetime.now().strftime("%H:%M:%S")
        line = f"[{t}] {text}"
        if not os.path.exists(outdir):
            with open(pathlib.Path(outdir, "conodictor.log"), "w"):
                pass

        logging.basicConfig(
            filename=pathlib.Path(outdir, "conodictor.log"),
            level=logging.INFO,
        )

        logging.info(line)

    def translate_seq(seq):
        """
        Translate DNA sequence to proteins.
        """
        seqlist = []
        # frame 1
        seqlist.append(translate(seq))
        # frame 2
        seqlist.append(translate(seq[1:]))
        # frame 3
        seqlist.append(translate(seq[2:]))
        # frame 4
        seqlist.append(translate(reverse_complement(seq)))
        # frame 5
        seqlist.append(translate(reverse_complement(seq)[1:]))
        # frame 6
        seqlist.append(translate(reverse_complement(seq)[2:]))

        return seqlist

    def do_translation(infile, outfile, sw=60):

        seqin = pyfastx.Fasta(infile)
        with open(pathlib.Path(f"{outfile}_proteins.fa"), "w") as protfile:
            for sequence in seqin:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    protseq = translate_seq(sequence.seq)
                    for idx, frame in enumerate(protseq):
                        # Rule E203 from flacke8 check for extraneous
                        # whitespace before a colon. But black follow
                        # PEP8 rules.
                        # A PR is open to resolve this issue:
                        # https://github.com/PyCQA/pycodestyle/pull/914
                        seq_letters = [
                            frame[i : i + sw]  # noqa: E203
                            for i in range(0, len(frame), sw)
                        ]
                        nl = "\n"
                        protfile.write(
                            f">{sequence.name}_frame={idx + 1}\n"
                            + f"{nl.join(map(str, seq_letters))}\n"
                        )

    VERSION = "2.1.3"

    # Define start time------------------------------------------------------
    startime = datetime.now()

    # Handling db directory path specification-------------------------------
    dbdir = pathlib.Path(os.path.dirname(os.path.realpath(__file__)), "db")

    # Handling output directory creation-------------------------------------
    if os.path.isdir(outdir):
        if force:
            print(f"Reusing outdir {outdir}")
            shutil.rmtree(outdir)
            os.mkdir(outdir)
        else:
            print(
                f"conodictor: error: Your choosen output folder '{outdir}'"
                + " already exist!. Please change it using outdir option"
                + " or use force=True to reuse it.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(f"Creating output directory {outdir}")
        os.mkdir(outdir)

    # Start program ---------------------------------------------------------
    msg(f"This is conodictor {VERSION}")
    msg(f"Localtime is {datetime.now().strftime('%H:%M:%S')}")

    # Getting version of tools ----------------------------------------------
    sub_hmmsearch = subprocess.run(["hmmsearch", "-h"], capture_output=True)
    hmmsearch_match = re.findall(
        r"# HMMER\s+(\d+\.\d+)", sub_hmmsearch.stdout.decode("utf-8")
    )

    sub_pfscan = subprocess.run(["pfscanV3", "-h"], capture_output=True)
    pfscan_match = re.findall(
        r"Version\s+(\d+\.\d+\.\d+)", sub_pfscan.stdout.decode("utf-8")
    )

    # Input sequence file manipulation---------------------------------------

    # Open fasta file (build file index)
    infa = pyfastx.Fasta(infile)

    # Test if file type is accepted
    if test_sequence(infa[1].seq) in ["DNA", "protein"]:
        pass
    else:
        msg(
            "Your file is not a DNA or protein file, please provide a DNA or"
            + " protein fasta file"
        )
        sys.exit(1)

    # Test if file is gziped and translate
    if infa.is_gzip:
        # Decompress file
        msg("Your file is gzip compressed. Decompressing it.")
        with gzip.open(infile, "r") as seqh:
            with open(
                pathlib.Path(outdir, pathlib.Path(infile).stem), "wb"
            ) as seqo:
                shutil.copyfileobj(seqh, seqo)
            seqo.close()
        msg("Decompression done.")

        # Read decompressed file
        ingzfa = pyfastx.Fasta(
            str(pathlib.Path(outdir, pathlib.Path(infile).stem))
        )

        # Test if alphabet is DNA, or protein and translate or not
        if test_sequence(ingzfa[1].seq) == "DNA":
            msg("You provided DNA fasta file")
            msg("Translating input sequences")
            do_translation(
                str(pathlib.Path(outdir, pathlib.Path(infile).stem)),
                str(pathlib.Path(outdir, pathlib.Path(infile).stem)),
            )
            msg("Translation done!")
            inpath = pathlib.Path(
                outdir, f"{pathlib.Path(infile).stem}_proteins.fa"
            )
        elif test_sequence(ingzfa[1].seq) == "protein":
            msg("You provided protein fasta file")
            inpath = pathlib.Path(outdir, pathlib.Path(infile).stem)

    elif not infa.is_gzip:
        msg("Your file is not gzip compressed")
        if test_sequence(infa[1].seq) == "DNA":
            msg("You provided DNA fasta file")
            msg("Translating input sequences")
            do_translation(
                str(pathlib.Path(infile)),
                str(pathlib.Path(outdir, pathlib.Path(infile).stem)),
            )
            msg("Translation done!")
            inpath = pathlib.Path(
                outdir, f"{pathlib.Path(infile).stem}_proteins.fa"
            )
        elif test_sequence(infa[1].seq) == "protein":
            msg("You provided protein fasta file")
            inpath = infile

    # Get sequence keys
    infile = pyfastx.Fasta(str(inpath))
    seqids = infile.keys()

    # HMMs-------------------------------------------------------------------
    msg("Running HMM prediction")
    msg(f"Using hmmsearch v{hmmsearch_match[0]}")
    subprocess.run(
        [
            "hmmsearch",
            "-E",
            "0.1",
            "--noali",
            "-o",
            pathlib.Path(outdir, "out.hmmer"),
            pathlib.Path(dbdir, "conodictor.hmm"),
            inpath,
        ]
    )

    hmmdict = defaultdict(lambda: defaultdict(list))

    with open(pathlib.Path(outdir, "out.hmmer")) as hmmfile:
        for record in SearchIO.parse(hmmfile, "hmmer3-text"):
            hits = record.hits
            for hit in hits:
                hmmdict[hit.id][record.id.split("_")[1]].append(hit.evalue)
    hmmfile.close()

    hmmscore = hmm_threshold(hmmdict)
    hmmfam = get_hmm_fam(hmmscore)

    msg("Done with HMM prediction")

    # PSSMs------------------------------------------------------------------
    msg("Running PSSM prediction")
    msg(f"Using pfscan v{pfscan_match[0]}")
    pssm_run = subprocess.run(
        [
            "pfscanV3",
            "-o",
            "7",
            pathlib.Path(dbdir, "conodictor.pssm"),
            "-f",
            inpath,
        ],
        capture_output=True,
    )

    with open(pathlib.Path(outdir, "out.pssm"), "w") as po:
        po.write(pssm_run.stdout.decode("utf-8"))
    po.close()

    pssmdict = defaultdict(list)

    with open(pathlib.Path(outdir, "out.pssm")) as pssmfile:
        rd = csv.reader(pssmfile, delimiter="\t")
        for row in rd:
            pssmdict[row[3]].append((row[0].split("|")[0]).split("_")[1])
    pssmfile.close()

    pssmfam = get_pssm_fam(pssmdict)

    msg("Done with PSSM predictions")

    # Writing output---------------------------------------------------------
    msg("Writing output")
    finalfam = defaultdict(list)
    for sid in seqids:
        if sid in hmmfam and sid in pssmfam:
            finalfam[sid].extend(
                [hmmfam[sid], pssmfam[sid], cdpred(hmmfam[sid], pssmfam[sid])]
            )
        elif sid in hmmfam and sid not in pssmfam:
            finalfam[sid].extend([hmmfam[sid], "UNKNOWN", hmmfam[sid]])
        elif sid in pssmfam and sid not in hmmfam:
            finalfam[sid].extend(["UNKNOWN", pssmfam[sid], pssmfam[sid]])
        else:
            finalfam[sid].extend(["UNKOWN", "UNKOWN", "UNKNOWN"])

    outfile = open(pathlib.Path(outdir, "summary.txt"), "a")
    outfile.write("sequence\thmm_pred\tpssm_pred\tdefinitive_pred\n")
    if not allres:
        uniq_final = {
            k: v
            for k, v in finalfam.items()
            if bool(set(v).intersection(["UNKNOWN", "UNKNOWN", "UNKNOWN"]))
            is False
        }
        for uk, uv in uniq_final.items():
            outfile.write(f"{uk}\t{uv[0]}\t{uv[1]}\t{uv[2]}\n")
        outfile.close()
    else:
        for k, v in finalfam.items():
            outfile.write(f"{k}\t{v[0]}\t{v[1]}\t{v[2]}\n")
        outfile.close()
    msg("Done with writing output.")

    # Finishing -------------------------------------------------------------
    os.remove(pathlib.Path(outdir, "out.hmmer"))
    os.remove(pathlib.Path(outdir, "out.pssm"))
    os.remove(pathlib.Path(f"{inpath}.fxi"))
    msg("Classification finished successfully.")
    msg("Creating donut plot")
    donut_graph()
    msg("Done creating donut plot")
    msg("Creating zip file")
    shutil.make_archive(outdir, "zip", outdir)
    msg("Done creating zip file")
    msg(f"Check {outdir}.zip folder for results")
    endtime = datetime.now()
    walltime = endtime - startime
    msg(f"Walltime used (hh:mm:ss.ms): {walltime}")
    if len(seqids) % 2:
        msg("Nice to have you. Share, enjoy and come back!")
    else:
        msg("Thanks you, come again.")
