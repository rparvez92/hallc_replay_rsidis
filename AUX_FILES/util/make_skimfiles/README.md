## Machinery to create skim files out of R-SIDIS hcana ROOT files

How-to:
1. Create a run list with the desired run numbers to analyze (e.g. sidis_runlist_pass0.txt etc.).
2. Open up submit_run_make_skimfile.sh in an editor.
3. Set up the $SCRIPT_DIR path appropriately. Read the description of the arguments.
4. Execute `submit_run_make_skimfile.sh` with the proper arguments: `./submit_run_make_skimfile.sh <runlist> <runtype> <root_dir> <run_on_ifarm> [report_dir]`. The optional report directory defaults to the ROOT input directory.

Supported run types are `SIDIS`, `HMSHEEP`, `SHMSHEEP`, `HMSDIS`, and `SHMSDIS`.
For HEEP data, the prefix names the electron arm: `HMSHEEP` means the electron is
in HMS, while `SHMSHEEP` means the electron is in SHMS. The old ambiguous `HEEP`
run type is rejected.

The skim macro also writes reconstructed branches with a `_recon`
suffix. Their inputs and applicability are documented in
`recon_branch_dependencies.csv`. The existing loose cuts continue to use the
original branches.
Following the `recon_hcana` convention, reconstructed lab vectors are built
directly from `gtr.p_recon`, `gtr.th_recon`, the original `gtr.ph`, the nominal
spectrometer `Angle` in the replay report, and the fixed phi/OOP geometry
constants in the macro. The incident electron is built from the report beam
energy along lab +z, and reconstructed primary and recoil four-vectors are then
calculated from scratch. `gtr.dp` is retained only as an original branch; no
`dp_recon` branch is produced because dp is an optics reconstruction quantity.
For SIDIS, `z_recon` follows the analysis convention `p_recon / nu_recon`,
using the detected-hadron momentum magnitude rather than its energy. An
unphysical reconstructed `W^2 <= 0` is represented by HCANA's `1e38` sentinel
rather than by zero.

Description of the scripts:
1. make_skimmed_rootfile.C : Main script written in C++. It creates a skim file for a given run. The loose analysis cuts, reconstructed kinematics, and list of ROOT variables to be copied to the skimmed files are defined within. Run-dependent beam energy, target/particle masses, and nominal central `Angle` values are read by label from the matching replay report. `Angle True` and `Angle Offset` are not used. The report directory is independent of the ROOT input directory.
2. run_make_skimfile.sh : It is a shell script to execute make_skimmed_rootfile.C script with appropriate arguments and environment setup.
3. submit_run_make_skimfile.sh : It is a wrapper script to run the run_make_skimfile.sh script. It reads from a run list (a single-column txt file w/ run numbers) and calls run_make_skimfile.sh for each run. User can choose whether they want to run the jobs on ifarm or submit them to the batch farm.
