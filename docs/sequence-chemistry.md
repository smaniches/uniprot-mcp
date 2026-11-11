# Sequence chemistry: scope, methods and checks

`uniprot_compute_properties` and the "Sequence chemistry" section of
`uniprot_target_dossier` derive seven properties from a UniProt sequence.
This page says which sequence they use, how each property is computed,
what the results were checked against, and where the estimates stop
being reliable.

## Which sequence is used

Both tools take the **canonical sequence of the entry's FASTA record as
it is**. Nothing is removed. A signal peptide, a propeptide, a transit
peptide or an initiator methionine annotated on the entry is part of the
calculation, so for a secreted or otherwise processed protein the values
describe the precursor and not the mature chain. Every result says so:
`sequence_scope` in JSON, "Sequence basis" in Markdown.

Human insulin shows the size of the difference. For `P01308` the tools
report 110 residues, 11,980.9 Da and a pI of 5.22. Those are the figures
for preproinsulin. The entry annotates a signal peptide (residues 1 to
24), the B chain (25 to 54), the C peptide (57 to 87) and the A chain (90
to 110); mature insulin is the B and A chains only.

`uniprot_get_processing_features` lists these boundaries for any entry.
The server has no tool that computes properties for part of a sequence.
To characterise a mature chain, take its residues from
`uniprot_get_sequence` and use a tool that accepts a sequence.

Two further points about the input:

- Letters other than the 20 standard amino acids (`U`, `O`, `B`, `Z`, `X`)
  are counted under `other` in the composition and left out of every
  property, the length included.
- ExPASy Compute pI/Mw, when it is given UniProtKB identifiers, computes
  for the mature chains and peptides of the entries or for a region the
  user selects
  ([documentation](https://web.expasy.org/compute_pi/pi_tool-doc.html)),
  so the value it shows for an accession is not the value this server
  reports for a processed protein. To compare like with like, give both
  the same sequence.

## Methods

| Property | Method |
|---|---|
| Length | Number of standard residues. |
| Molecular weight | Sum of average residue masses plus one water. |
| Net charge at pH 7 | Henderson-Hasselbalch sum over the amino terminus, the carboxyl terminus and the ionizable side chains, each treated as independent with the fixed pK listed below. |
| Theoretical pI | The pH at which that net charge is zero, found by bisection over pH 0 to 14 and reported to two decimals. |
| GRAVY | Mean Kyte-Doolittle hydropathy of the residues (Kyte and Doolittle 1982). |
| Aromaticity | Fraction of Phe, Trp and Tyr. |
| Extinction coefficient at 280 nm | 5500 per Trp plus 1490 per Tyr, in M⁻¹·cm⁻¹ (Pace et al. 1995). All cysteines are taken as reduced; the tools do not add the 125 per cystine of that formula. |

## The pK set

The theoretical pI and the net charge use the Bjellqvist pK set.

| Group | pK |
|---|---|
| Amino terminus | 7.50. When the first residue is one of the following, its own value applies: Ala 7.59, Glu 7.70, Met 7.00, Pro 8.36, Ser 6.93, Thr 6.82, Val 7.44. |
| Carboxyl terminus | 3.55 |
| Asp side chain | 4.05 |
| Glu side chain | 4.45 |
| His side chain | 5.98 |
| Cys side chain | 9.00 |
| Tyr side chain | 10.00 |
| Lys side chain | 10.00 |
| Arg side chain | 12.00 |

The numbers are those tabulated in Biopython 1.88
(`Bio.SeqUtils.IsoelectricPoint`), which attributes them to Bjellqvist et
al. 1993 and 1994. The table was taken from that source file; the two
papers were not consulted for the individual values. ExPASy states that
its Compute pI/Mw tool calculates the pI with pK values described by
Bjellqvist et al., and that ProtParam calculates the pI as Compute pI/Mw
does.

Every result names the set and the terminal values applied to that
sequence: `charge_model` in JSON, "pI and charge model" in Markdown.

### One rule differs from Biopython

After a C-terminal Asp or Glu, Biopython 1.88 raises the pK of the
carboxyl terminus from 3.55 to 4.55 or 4.75. ExPASy ProtParam and Compute
pI/Mw both return 3.80 for `GGGGGGGGGD` and for `GGGGGGGGDG`, the same
composition with the Asp one position earlier. Biopython, searched over
the whole pH scale, returns 4.30 for the first and 3.80 for the second.
This server keeps a single C-terminal pK and so follows the ExPASy
result. On the proteins below the difference from Biopython is at most
0.05 pH and appears only for acidic proteins that end in Asp or Glu.

Biopython's `pi()` searches pH 4.05 to 12 by default and returns the
bound when the root lies outside. For prothymosin alpha it returns 4.05;
searched over the whole scale (`pi(7.0, 0.0, 14.0)`) it returns 3.69.
This server always searches pH 0 to 14.

## What the results were checked against

Measured on 2026-11-11 with UniProt release 2026_04 sequences, ExPASy
ProtParam as served that day and Biopython 1.88.

**Theoretical pI, 27 proteins.** Equal to ProtParam for 27 of 27. The
last column is the value that server versions up to and including 1.3.17
returned with their earlier pK table: it differs from ProtParam by more
than 0.01 for 25 of the 27, by 0.92 at most.

| Entry | Sequence version | Residues | ProtParam | This server | Biopython 1.88 | Server up to 1.3.17 |
|---|---|---|---|---|---|---|
| `P04637` P53_HUMAN | 4 | 393 | 6.33 | 6.33 | 6.33 | 6.36 |
| `P01308` INS_HUMAN | 1 | 110 | 5.22 | 5.22 | 5.22 | 4.93 |
| `P69905` HBA_HUMAN | 2 | 142 | 8.72 | 8.72 | 8.72 | 9.32 |
| `P68871` HBB_HUMAN | 2 | 147 | 6.74 | 6.74 | 6.74 | 6.92 |
| `P00918` CAH2_HUMAN | 2 | 260 | 6.87 | 6.87 | 6.87 | 7.07 |
| `P62942` FKB1A_HUMAN | 2 | 108 | 7.89 | 7.89 | 7.89 | 8.81 |
| `P02768` ALBU_HUMAN | 2 | 609 | 5.92 | 5.92 | 5.92 | 5.85 |
| `P61626` LYSC_HUMAN | 1 | 148 | 9.38 | 9.38 | 9.38 | 9.55 |
| `P0DP23` CALM1_HUMAN | 1 | 149 | 4.09 | 4.09 | 4.09 | 3.81 |
| `P01112` RASH_HUMAN | 1 | 189 | 5.16 | 5.16 | 5.16 | 4.90 |
| `P38398` BRCA1_HUMAN | 2 | 1863 | 5.29 | 5.29 | 5.29 | 5.03 |
| `P00533` EGFR_HUMAN | 2 | 1210 | 6.26 | 6.26 | 6.26 | 6.26 |
| `P10636` TAU_HUMAN | 5 | 758 | 6.25 | 6.25 | 6.25 | 6.26 |
| `P68431` H31_HUMAN | 2 | 136 | 11.13 | 11.13 | 11.13 | 11.62 |
| `P02144` MYG_HUMAN | 2 | 154 | 7.14 | 7.14 | 7.14 | 7.72 |
| `P42212` GFP_AEQVI | 1 | 238 | 5.67 | 5.67 | 5.67 | 5.62 |
| `P00698` LYSC_CHICK | 1 | 147 | 9.36 | 9.36 | 9.36 | 9.40 |
| `P0CG48` UBC_HUMAN | 3 | 685 | 7.16 | 7.16 | 7.16 | 7.83 |
| `P05067` A4_HUMAN | 3 | 770 | 4.73 | 4.73 | 4.73 | 4.43 |
| `P12931` SRC_HUMAN | 3 | 536 | 7.10 | 7.10 | 7.10 | 7.27 |
| `P07900` HS90A_HUMAN | 5 | 732 | 4.94 | 4.94 | 4.94 | 4.63 |
| `P08238` HS90B_HUMAN | 4 | 724 | 4.96 | 4.96 | 4.97 | 4.65 |
| `P0DMV8` HS71A_HUMAN | 1 | 641 | 5.47 | 5.47 | 5.48 | 5.24 |
| `P06454` PTMA_HUMAN | 2 | 111 | 3.66 | 3.66 | 3.69 | 3.37 |
| `P04271` S100B_HUMAN | 2 | 92 | 4.52 | 4.52 | 4.57 | 4.21 |
| `P37840` SYUA_HUMAN | 1 | 140 | 4.67 | 4.67 | 4.67 | 4.33 |
| `P27797` CALR_HUMAN | 1 | 417 | 4.29 | 4.29 | 4.29 | 4.02 |

The Biopython column is `pi(7.0, 0.0, 14.0)`. The first 20 rows are the
sample of the November 2026 audit that reported the earlier
disagreement; the last seven are acidic proteins, five of them ending in
Asp or Glu.

**Theoretical pI, 24 probe peptides.** Short sequences that each isolate
one rule: the amino terminus with each first residue that has its own
value, Asp or Glu at and next to the carboxyl terminus, compositions with
a pI below 4 or above 12, and the Cys and Tyr side chains. Equal to
ProtParam for 23 of 24. The remaining one is ten glycines, whose root is
exactly 5.525: ProtParam prints 5.52 and this server 5.53.

**Net charge at pH 7.** ProtParam does not report it. Against Biopython
1.88 the value is equal to four decimals for the 20 proteins that do not
end in Asp or Glu, and within 0.006 for the seven that do, which is the
effect of the C-terminal rule above.

**Properties this comparison did not change.** On the same 27 proteins
the molecular weight equals ProtParam's at its two decimals for all 27,
the extinction coefficient equals ProtParam's reduced-cysteine value for
the 26 where it reports one (prothymosin alpha has no Trp or Tyr), and
GRAVY is within 0.0005 of ProtParam's three-decimal value for all 27.

The checks are frozen in `tests/unit/test_proteinchem_pi_reference.py`.
To repeat one by hand, paste the canonical sequence of an entry into
[ProtParam](https://web.expasy.org/protparam/), or run
`Bio.SeqUtils.IsoelectricPoint.IsoelectricPoint(sequence).pi(7.0, 0.0, 14.0)`.

Agreement is established for these 51 sequences and no further. The
ExPASy tools are web services, and their output can change.

## Limits of the estimates

- **Sequence only.** Each ionizable group gets one fixed pK. The
  calculation knows nothing of folding, of bound ligands or metals, or of
  post-translational modification. Bjellqvist et al. 1994 report that
  N-terminal blocking in particular is a major obstacle to calculating a
  pI from sequence. Every cysteine is counted as a free thiol, including
  those that form disulfide bonds.
- **Where the pK set comes from.** Bjellqvist et al. 1993 determined the
  focusing positions of polypeptides under denaturing conditions.
  ExPASy's documentation describes the pK values as defined from
  migration between pH 4.5 and 7.3 in immobilised pH gradient gels with
  9.2 M and 9.8 M urea, cautions that predictions for highly basic
  proteins may not be adequate, and notes that small proteins with little
  buffer capacity are predicted less accurately.
- **Extinction coefficient.** Pace et al. 1995 find the prediction quite
  reliable for proteins that contain Trp and less so for those that do
  not, and recommend measuring.
- **Precursor, not mature chain.** See the first section.
- **Earlier values.** A pI or net charge obtained from version 1.3.17 or
  earlier used a different pK table and is not comparable with current
  output. Molecular weight, GRAVY, aromaticity and the extinction
  coefficient are computed exactly as before.

## References

- Bjellqvist B, Hughes GJ, Pasquali C, Paquet N, Ravier F, Sanchez JC,
  Frutiger S, Hochstrasser D. The focusing positions of polypeptides in
  immobilized pH gradients can be predicted from their amino acid
  sequences. *Electrophoresis* 14, 1023-1031 (1993).
  [doi:10.1002/elps.11501401163](https://doi.org/10.1002/elps.11501401163)
- Bjellqvist B, Basse B, Olsen E, Celis JE. Reference points for
  comparisons of two-dimensional maps of proteins from different human
  cell types defined in a pH scale where isoelectric points correlate
  with polypeptide compositions. *Electrophoresis* 15, 529-539 (1994).
  [doi:10.1002/elps.1150150171](https://doi.org/10.1002/elps.1150150171)
- Kyte J, Doolittle RF. A simple method for displaying the hydropathic
  character of a protein. *J Mol Biol* 157, 105-132 (1982).
  [doi:10.1016/0022-2836(82)90515-0](https://doi.org/10.1016/0022-2836(82)90515-0)
- Pace CN, Vajdos F, Fee L, Grimsley G, Gray T. How to measure and
  predict the molar absorption coefficient of a protein. *Protein Sci* 4,
  2411-2423 (1995).
  [doi:10.1002/pro.5560041120](https://doi.org/10.1002/pro.5560041120)
- ExPASy ProtParam documentation:
  <https://web.expasy.org/protparam/protparam-doc.html>
- ExPASy Compute pI/Mw documentation:
  <https://web.expasy.org/compute_pi/pi_tool-doc.html>
