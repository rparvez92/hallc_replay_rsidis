#include <vector>
#include "ROOT/RDataFrame.hxx"
#include <stdio.h>
#include <iostream>
#include "TSystem.h"
#include <Math/Vector4D.h>

const double Mp = 0.938272;

// Common SHMS vairables
std::vector<std::string> shmsVars = {
    "P.gtr.x", "P.gtr.y", "P.gtr.dp", "P.gtr.p", "P.gtr.ph", "P.gtr.th", "P.gtr.beta", "P.gtr.index",
    "P.dc.x_fp", "P.dc.y_fp", "P.dc.xp_fp", "P.dc.yp_fp", "P.dc.InsideDipoleExit",
    "P.ngcer.npeSum", "P.hgcer.npeSum", "P.aero.npeSum", "P.cal.etottracknorm",
    "P.react.x", "P.react.y", "P.react.z",
    "P.hod.goodstarttime","P.hod.fpHitsTime"};

// SHMS DIS kin & raster variables
std::vector<std::string> shmskinVars = {
    "P.kin.x_bj", "P.kin.Q2", "P.kin.nu", "P.kin.W",
    "P.rb.raster.frxaRawAdc", "P.rb.raster.frxbRawAdc", "P.rb.raster.fryaRawAdc", "P.rb.raster.frybRawAdc"};

// Common HMS variables
std::vector<std::string> hmsVars = {
    "H.gtr.x", "H.gtr.y", "H.gtr.dp", "H.gtr.p", "H.gtr.ph", "H.gtr.th", "H.gtr.beta", "H.gtr.index",
    "H.dc.x_fp", "H.dc.y_fp", "H.dc.xp_fp", "H.dc.yp_fp", "H.dc.InsideDipoleExit",
    "H.cer.npeSum", "H.cal.etottracknorm",
    "H.react.x", "H.react.y", "H.react.z",
    "H.hod.goodstarttime","H.hod.fpHitsTime"};

// HMS DIS kin & raster variables
std::vector<std::string> hmskinVars = {
    "H.kin.x_bj", "H.kin.Q2", "H.kin.nu", "H.kin.W",
    "H.rb.raster.fr_xa", "H.rb.raster.fr_xb", "H.rb.raster.fr_ya", "H.rb.raster.fr_yb"};

// Common coin data (SIDIS) vairiables
std::vector<std::string> ctimeVars = {
    "CTime.ePiCoinTime_ROC1", "CTime.ePiCoinTime_ROC2",
    "CTime.epCoinTime_ROC1", "CTime.epCoinTime_ROC2",
    "CTime.CoinTime_RAW_ROC1", "CTime.CoinTime_RAW_ROC2",
    "T.coin.hRF_tdcTime", "T.coin.pRF_tdcTime",
    "H.kin.primary.x_bj", "H.kin.primary.Q2", "H.kin.primary.nu", "H.kin.primary.W",
    "P.kin.secondary.th_xq", "P.kin.secondary.ph_xq", "P.kin.secondary.MMpi",
    "T.helicity.helicity", "T.helicity.hel",
    "H.rb.raster.frxaRawAdc", "H.rb.raster.frxbRawAdc", "H.rb.raster.fryaRawAdc", "H.rb.raster.frybRawAdc",
    "P.rb.raster.frxaRawAdc", "P.rb.raster.frxbRawAdc", "P.rb.raster.fryaRawAdc", "P.rb.raster.frybRawAdc"};

// Common HEEP variables
std::vector<std::string> heepVars = {
    "CTime.epCoinTime_ROC1", "CTime.epCoinTime_ROC2",
    "CTime.CoinTime_RAW_ROC1", "CTime.CoinTime_RAW_ROC2",
    "T.coin.hRF_tdcTime", "T.coin.pRF_tdcTime",
    "P.kin.primary.x_bj", "P.kin.primary.Q2", "P.kin.primary.nu", "P.kin.primary.W",
    "H.kin.secondary.th_xq", "H.kin.secondary.ph_xq",
    "H.rb.raster.frxaRawAdc", "H.rb.raster.frxbRawAdc", "H.rb.raster.fryaRawAdc", "H.rb.raster.frybRawAdc",
    "P.rb.raster.frxaRawAdc", "P.rb.raster.frxbRawAdc", "P.rb.raster.fryaRawAdc", "P.rb.raster.frybRawAdc"};

// // BCM variables
// std::vector<std::string> bcmVars = {
//   "ibcm1", "ibcm2"
// };

std::vector<std::string> get_varnames(const std::string &runtype)
{
  // Returns a vector of variable names based on the run type
  auto concat = [](std::vector<std::string> base,
                   const std::vector<std::string> &add)
  {
    base.insert(base.end(), add.begin(), add.end());
    return base;
  };

  if (runtype == "SIDIS")
  {
    auto vars = shmsVars;
    vars.insert(vars.end(), hmsVars.begin(), hmsVars.end());
    vars.insert(vars.end(), ctimeVars.begin(), ctimeVars.end());
    // vars.insert(vars.end(), bcmVars.begin(), bcmVars.end());
    return vars;
  }
  else if (runtype == "HEEP")
  {
    auto vars = shmsVars;
    vars.insert(vars.end(), hmsVars.begin(), hmsVars.end());
    vars.insert(vars.end(), heepVars.begin(), heepVars.end());
    // vars.insert(vars.end(), bcmVars.begin(), bcmVars.end());
    return vars;
  }
  else if (runtype == "SHMSDIS")
  {
    auto vars = shmsVars;
    vars.insert(vars.end(), shmskinVars.begin(), shmskinVars.end());
    // vars.insert(vars.end(), bcmVars.begin(), bcmVars.end());
    return vars;
  }
  else if (runtype == "HMSDIS")
  {
    auto vars = hmsVars;
    vars.insert(vars.end(), hmskinVars.begin(), hmskinVars.end());
    // vars.insert(vars.end(), bcmVars.begin(), bcmVars.end());
    return vars;
  }
  else
  {
    std::cout << "Invalid runtype specified! Choose from SIDIS, HEEP, SHMSDIS, HMSDIS.\n";
    return {};
  }
}

std::string get_anacuts(std::string runtype)
{
  // Returns loose Analysis cuts based on the run type
  std::string hmscuts_gen = "H.gtr.index>-1 && abs(H.gtr.dp)<12. ";
  std::string hmscuts_pid = "H.cer.npeSum>1"; // HMS PID cut for electrons
  std::string hmscuts = hmscuts_gen + " && " + hmscuts_pid;
  std::string shmscuts = "P.gtr.index>-1 && abs(P.gtr.dp)<30.";
  std::string sidiscuts = hmscuts + " && " + shmscuts;
  std::string heepcuts = hmscuts_gen + " && " + shmscuts;

  if (runtype == "SIDIS")
  {
    return sidiscuts;
  }
  else if (runtype == "HEEP")
  {
    return heepcuts;
  }
  else if (runtype == "SHMSDIS")
  {
    return shmscuts;
  }
  else if (runtype == "HMSDIS")
  {
    return hmscuts;
  }
  else
  {
    std::cout << "Invalid runtype specified! Choose from SIDIS, HEEP, SHMSDIS, HMSDIS.\n";
    return "";
  }
}

// Function to add an item to a vector if it's not already present
auto add_if_missing = [](std::vector<std::string> &vec, const std::string &item)
{
  if (std::find(vec.begin(), vec.end(), item) == vec.end())
  {
    vec.push_back(item);
  }
};

void log_peak_memory()
{
  std::ifstream status_file("/proc/self/status");
  std::string label;
  while (status_file >> label)
  {
    if (label == "VmHWM:")
    { // Peak resident set size
      unsigned long peak_kb;
      status_file >> peak_kb;
      std::string unit;
      status_file >> unit;
      std::cout << "[MEMORY] Peak RSS: " << peak_kb << " kB" << std::endl;
      break;
    }
  }
  // Handy unix command
  // grep "\[MEMORY\]" *.out | sort -nk4
}

double get_beam_energy_for_this_run(int run)
{
  std::map<std::pair<int, int>, double> runrange_to_energy = {
      {{23834, 24874}, 8.5831},
      {{24875, 25603}, 10.6716},
      {{27101, 27755}, 6.4724},
      {{27756, 28106}, 8.5814},
      {{28107, 28471}, 10.6759}};

  // Iterate to find if 'run' is between the first and second of any pair
  for (auto const &[range, energy] : runrange_to_energy)
  {
    if (run >= range.first && run <= range.second)
    {
      return energy;
    }
  }
  // for invalid run numbers
  std::cerr << "WARNING: Run number " << run << " not found in energy map!\n";
  std::cerr << "Missing mass calculation will be inaccurate!\n";
  return -999.0; // Return an unphysical energy to flag the issue
}

void make_skimmed_rootfile(int run,             // run number to process
                           std::string runtype, // SIDIS, HEEP, SHMSDIS, HMSDIS
                           std::string indir,   // input directory containing replayed root files
                           std::string outdir   // output directory to save skimmed root files
)
{
  // Defining input root file name based on run type
  std::string rfilename = Form("coin_replay_production_%d_-1.root", run); // SIDIS and HEEP
  if (runtype == "SHMSDIS")
  {
    rfilename = Form("shms_coin_replay_production_%d_-1.root", run);
  }
  else if (runtype == "HMSDIS")
  {
    rfilename = Form("hms_coin_replay_production_%d_-1.root", run);
  }
  std::string inrootfile = Form("%s/%s", indir.c_str(), rfilename.c_str());

  // Check if input root file exists
  if (gSystem->AccessPathName(inrootfile.c_str()))
  {
    std::cerr << "Input root file does not exist: " << inrootfile << std::endl;
    return;
  }

  // Create RDataFrame from the input root file
  ROOT::RDataFrame df("T", inrootfile.c_str());

  // apply loose analysis cuts
  auto df_filtered = df.Filter(get_anacuts(runtype));

  if (runtype == "SIDIS")
  {
    std::cout << "Adding extra columns for SIDIS run type...\n";

    std::string z = "P.gtr.p/H.kin.primary.nu";
    std::string pt = "sqrt(pow(P.gtr.p,2)*(1.-pow(cos(P.kin.secondary.th_xq),2)))";
    std::string ptx = pt + "*cos(P.kin.secondary.ph_xq)";
    std::string pty = pt + "*sin(P.kin.secondary.ph_xq)";
    // calculat missing mass using 4-vector arithmetic in a lambda function
    double Ein = get_beam_energy_for_this_run(run);
    auto calc_mm = [Ein](double epx, double epy, double epz, double ep,
                         double ppx, double ppy, double ppz, double pp)
    {
      // Define 4-vectors
      ROOT::Math::PxPyPzEVector Pe(0, 0, Ein, Ein);
      ROOT::Math::PxPyPzEVector Peprime(epx, epy, epz, ep);
      ROOT::Math::PxPyPzEVector Pp(0, 0, 0, Mp);
      ROOT::Math::PxPyPzEVector Phadron(ppx, ppy, ppz, pp);
      // Perform 4-vector arithmetic
      auto Pmiss = (Pe - Peprime + Pp) - Phadron;
      return Pmiss.M();
    };

    // defining new columns
    df_filtered = df_filtered
                      .Define("z", z.c_str())
                      .Define("pt", pt.c_str())
                      .Define("ptx", ptx.c_str())
                      .Define("pty", pty.c_str())
                      .Define("mmass", calc_mm,
                              {"H.gtr.px", "H.gtr.py", "H.gtr.pz", "H.gtr.p", "P.gtr.px", "P.gtr.py", "P.gtr.pz", "P.gtr.p"});

    // add these new variables to ctimeVars for output
    add_if_missing(ctimeVars, "z");
    add_if_missing(ctimeVars, "pt");
    add_if_missing(ctimeVars, "ptx");
    add_if_missing(ctimeVars, "pty");
    add_if_missing(ctimeVars, "mmass");
  }

  // write out the skimmed root files
  df_filtered.Snapshot(
      "T",
      Form("%s/skimmed_%s", outdir.c_str(), rfilename.c_str()),
      get_varnames(runtype));
  std::cout << "Skimmed root file created for run " << run << "\n";

  // Log peak memory
  log_peak_memory();
}
