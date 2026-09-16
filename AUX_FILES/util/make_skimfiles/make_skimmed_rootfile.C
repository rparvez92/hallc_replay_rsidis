#include <vector>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include "ROOT/RDataFrame.hxx"
#include <stdio.h>
#include <iostream>
#include "TSystem.h"
#include <Math/Vector4D.h>
#include "TLorentzVector.h"
#include "TRotation.h"
#include "TMath.h"
#include "TVector3.h"

const double Mp = 0.938272;
const double Me = 0.000511;

// Placeholder corrections. Keep these at zero until the HEEP study provides
// the final arm-dependent values. Momentum is in GeV and angles are in radians.
const double H_GTR_P_OFFSET = 0.0;
const double H_GTR_TH_OFFSET = 0.0;
const double P_GTR_P_OFFSET = 0.0;
const double P_GTR_TH_OFFSET = 0.0;

struct ReplayParameters
{
  double beamMomentum = 0.0;
  double targetMass = 0.0;
  double hPartMass = 0.0;
  double pPartMass = 0.0;
  double hOopOffset = 0.0;
  double pOopOffset = 0.0;
  TRotation hToLab;
  TRotation pToLab;
};

struct PrimaryKinematics
{
  TLorentzVector beam;
  TLorentzVector scattered;
  TLorentzVector target;
  TLorentzVector q;
  double xbj = 0.0;
  double Q2 = 0.0;
  double nu = 0.0;
  double W = 0.0;
};

struct SecondaryKinematics
{
  double th_xq = 0.0;
  double ph_xq = 0.0;
  double pmiss_y = 0.0;
  double pmiss_z = 0.0;
  double emiss = 0.0;
};

std::string trim(const std::string &text)
{
  const auto first = text.find_first_not_of(" \t\r\n");
  if (first == std::string::npos)
    return "";
  const auto last = text.find_last_not_of(" \t\r\n");
  return text.substr(first, last - first + 1);
}

bool run_matches(const std::string &selector, int run)
{
  std::stringstream ranges(selector);
  std::string range;
  while (std::getline(ranges, range, ','))
  {
    range = trim(range);
    if (range.empty())
      continue;
    const auto dash = range.find('-');
    try
    {
      if (dash == std::string::npos)
      {
        if (run == std::stoi(range))
          return true;
      }
      else
      {
        const int low = std::stoi(trim(range.substr(0, dash)));
        const int high = std::stoi(trim(range.substr(dash + 1)));
        if (run >= low && run <= high)
          return true;
      }
    }
    catch (const std::exception &)
    {
      return false;
    }
  }
  return false;
}

void load_parameter_file(const std::string &filename, int run,
                         const std::string &repoRoot,
                         std::map<std::string, std::string> &values,
                         int depth = 0)
{
  if (depth > 30)
    throw std::runtime_error("Parameter include depth exceeded while reading " + filename);

  std::ifstream input(filename);
  if (!input)
    throw std::runtime_error("Cannot open HCANA parameter file: " + filename);

  bool active = true;
  bool collectingRanges = false;
  bool pendingMatch = false;
  std::string line;
  while (std::getline(input, line))
  {
    line = trim(line);
    if (line.empty() || line[0] == ';')
      continue;

    if (line.rfind("#include", 0) == 0)
    {
      if (!active)
        continue;
      const auto firstQuote = line.find('"');
      const auto lastQuote = line.find_last_of('"');
      if (firstQuote != std::string::npos && lastQuote > firstQuote)
      {
        const std::string relative = line.substr(firstQuote + 1, lastQuote - firstQuote - 1);
        load_parameter_file(repoRoot + "/" + relative, run, repoRoot, values, depth + 1);
      }
      continue;
    }

    const auto comment = line.find('#');
    if (comment != std::string::npos)
      line = trim(line.substr(0, comment));
    if (line.empty())
      continue;

    if (std::isdigit(static_cast<unsigned char>(line[0])) && line.find('=') == std::string::npos)
    {
      pendingMatch = (collectingRanges ? pendingMatch : false) || run_matches(line, run);
      collectingRanges = line.back() == ',';
      if (!collectingRanges)
      {
        active = pendingMatch;
        pendingMatch = false;
      }
      continue;
    }

    if (!active)
      continue;
    const auto equals = line.find('=');
    if (equals == std::string::npos)
      continue;
    std::string key = trim(line.substr(0, equals));
    std::string value = trim(line.substr(equals + 1));
    const auto semicolon = value.find(';');
    if (semicolon != std::string::npos)
      value = trim(value.substr(0, semicolon));
    if (value.size() >= 2 && value.front() == '"' && value.back() == '"')
      value = value.substr(1, value.size() - 2);
    values[key] = value;
  }
}

double get_number(const std::map<std::string, std::string> &values,
                  const std::string &key, double fallback, bool required = false)
{
  const auto found = values.find(key);
  if (found == values.end())
  {
    if (required)
      throw std::runtime_error("Required HCANA parameter is missing: " + key);
    return fallback;
  }
  try
  {
    return std::stod(found->second);
  }
  catch (const std::exception &)
  {
    throw std::runtime_error("HCANA parameter is not numeric: " + key + " = " + found->second);
  }
}

TRotation make_to_lab_rotation(double thetaGeoDeg, double phiGeoDeg)
{
  const double thGeo = thetaGeoDeg * TMath::DegToRad();
  const double phGeo = phiGeoDeg * TMath::DegToRad();
  const double x = std::sin(thGeo) * std::cos(phGeo);
  const double y = std::sin(phGeo);
  const double z = std::cos(thGeo) * std::cos(phGeo);
  const double thSph = std::acos(std::max(-1.0, std::min(1.0, z)));
  const double phSph = std::atan2(y, x);
  const double st = std::sin(thSph), ct = std::cos(thSph);
  const double sp = std::sin(phSph), cp = std::cos(phSph);
  const double norm = std::sqrt(ct * ct + st * st * cp * cp);
  TVector3 nx(st * st * sp * cp / norm, -norm, st * ct * sp / norm);
  TVector3 ny(ct / norm, 0.0, -st * cp / norm);
  TVector3 nz(st * cp, st * sp, ct);
  TRotation rotation;
  rotation.SetToIdentity().RotateAxes(nx, ny, nz);
  return rotation;
}

ReplayParameters load_replay_parameters(int run)
{
  std::string macroPath = gSystem->UnixPathName(__FILE__);
  std::string repoRoot = gSystem->DirName(macroPath.c_str());
  for (int i = 0; i < 3; ++i)
    repoRoot = gSystem->DirName(repoRoot.c_str());

  std::map<std::string, std::string> values;
  const std::string database = repoRoot + "/DBASE/COIN/standard.database";
  load_parameter_file(database, run, repoRoot, values);

  const auto general = values.find("g_ctp_parm_filename");
  const auto kinematics = values.find("g_ctp_kinematics_filename");
  if (general == values.end() || kinematics == values.end())
    throw std::runtime_error("Run is not covered by DBASE/COIN/standard.database");
  load_parameter_file(repoRoot + "/" + general->second, run, repoRoot, values);
  load_parameter_file(repoRoot + "/" + kinematics->second, run, repoRoot, values);

  ReplayParameters result;
  result.beamMomentum = get_number(values, "gpbeam", 0.0, true);
  result.targetMass = get_number(values, "gtargmass_amu", 0.0, true) * 0.9315;
  result.hPartMass = get_number(values, "hpartmass", Me);
  result.pPartMass = get_number(values, "ppartmass", Me);
  result.hOopOffset = get_number(values, "h_oopcentral_offset", 0.0);
  result.pOopOffset = get_number(values, "p_oopcentral_offset", 0.0);

  double hTheta = get_number(values, "htheta_lab", 0.0, true);
  double pTheta = get_number(values, "ptheta_lab", 0.0, true);
  hTheta += get_number(values, "hthetacentral_offset", 0.0) * TMath::RadToDeg();
  pTheta += get_number(values, "pthetacentral_offset", 0.0) * TMath::RadToDeg();
  const double hPhi = get_number(values, "hphi_lab", 0.0) +
                      get_number(values, "hphi_offset", 0.0) * TMath::RadToDeg();
  const double pPhi = get_number(values, "pphi_lab", 0.0) +
                      get_number(values, "pphi_offset", 0.0) * TMath::RadToDeg();
  result.hToLab = make_to_lab_rotation(hTheta, hPhi);
  result.pToLab = make_to_lab_rotation(pTheta, pPhi);
  return result;
}

TVector3 transport_to_lab(double p, double th, double ph,
                          double oopOffset, const TRotation &rotation)
{
  TVector3 vector(th + oopOffset, ph, 1.0);
  vector *= p / std::sqrt(1.0 + std::pow(th + oopOffset, 2) + ph * ph);
  return rotation * vector;
}

TVector3 adjusted_lab_momentum(double pRecon, double thRecon,
                               double pOriginal, double thOriginal, double phOriginal,
                               double pxOriginal, double pyOriginal, double pzOriginal,
                               double oopOffset, const TRotation &rotation)
{
  // Anchor the transformation to the lab vector stored by HCANA. This retains
  // the exact replay-time geometry at zero correction, while transforming only
  // the momentum change with HCANA's transport-to-lab convention.
  const TVector3 originalLab(pxOriginal, pyOriginal, pzOriginal);
  const TVector3 originalFromTransport =
      transport_to_lab(pOriginal, thOriginal, phOriginal, oopOffset, rotation);
  const TVector3 reconFromTransport =
      transport_to_lab(pRecon, thRecon, phOriginal, oopOffset, rotation);
  return originalLab + reconFromTransport - originalFromTransport;
}

PrimaryKinematics calculate_primary(const TVector3 &scatteredMomentum,
                                    const TVector3 &originalScatteredMomentum,
                                    double originalQx, double originalQy,
                                    double originalQz, double originalOmega,
                                    double particleMass,
                                    double targetMass)
{
  PrimaryKinematics result;
  result.scattered.SetVectM(scatteredMomentum, particleMass);
  TLorentzVector originalScattered;
  originalScattered.SetVectM(originalScatteredMomentum, particleMass);
  TLorentzVector originalQ(originalQx, originalQy, originalQz, originalOmega);
  result.q = originalQ - (result.scattered - originalScattered);
  result.beam = result.q + result.scattered;
  result.target.SetXYZM(0.0, 0.0, 0.0, targetMass);
  result.Q2 = -result.q.M2();
  result.nu = result.q.E();
  TLorentzVector proton;
  proton.SetXYZM(0.0, 0.0, 0.0, 0.93827);
  const double W2 = (proton + result.q).M2();
  result.W = W2 > 0.0 ? std::sqrt(W2) : 1.0e38; // HCANA kBig for unphysical W2
  result.xbj = result.Q2 / (2.0 * 0.93827 * result.nu);
  return result;
}

SecondaryKinematics calculate_secondary(const PrimaryKinematics &primary,
                                        const TVector3 &secondaryMomentum,
                                        double secondaryMass)
{
  SecondaryKinematics result;
  TLorentzVector detected;
  detected.SetVectM(secondaryMomentum, secondaryMass);
  const TLorentzVector recoil = primary.target + primary.q - detected;
  TRotation toQ;
  toQ.SetZAxis(primary.q.Vect(), primary.scattered.Vect()).Invert();
  TVector3 xq = detected.Vect();
  TVector3 bq = recoil.Vect();
  xq *= toQ;
  bq *= toQ;
  const TVector3 pmiss = -bq;
  result.th_xq = xq.Theta();
  result.ph_xq = xq.Phi();
  result.pmiss_y = pmiss.Y();
  result.pmiss_z = pmiss.Z();
  result.emiss = primary.nu + primary.target.M() - detected.E();
  return result;
}

// Common SHMS vairables
std::vector<std::string> shmsVars = {
    "P.gtr.x", "P.gtr.y", "P.gtr.dp", "P.gtr.p", "P.gtr.ph", "P.gtr.th", "P.gtr.beta", "P.gtr.index",
    "P.dc.x_fp", "P.dc.y_fp", "P.dc.xp_fp", "P.dc.yp_fp", "P.dc.InsideDipoleExit",
    "P.ngcer.npeSum", "P.hgcer.npeSum", "P.aero.npeSum", "P.cal.etottracknorm",
    "P.react.x", "P.react.y", "P.react.z",
    "P.hod.goodstarttime"};

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
    "H.hod.goodstarttime"};

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

std::vector<std::string> hmsHeepVars = {
    "CTime.epCoinTime_ROC1", "CTime.epCoinTime_ROC2",
    "CTime.CoinTime_RAW_ROC1", "CTime.CoinTime_RAW_ROC2",
    "T.coin.hRF_tdcTime", "T.coin.pRF_tdcTime",
    "H.kin.primary.x_bj", "H.kin.primary.Q2", "H.kin.primary.nu", "H.kin.primary.W",
    "P.kin.secondary.th_xq", "P.kin.secondary.ph_xq",
    "P.kin.secondary.emiss", "P.kin.secondary.pmiss_y", "P.kin.secondary.pmiss_z",
    "H.rb.raster.frxaRawAdc", "H.rb.raster.frxbRawAdc", "H.rb.raster.fryaRawAdc", "H.rb.raster.frybRawAdc",
    "P.rb.raster.frxaRawAdc", "P.rb.raster.frxbRawAdc", "P.rb.raster.fryaRawAdc", "P.rb.raster.frybRawAdc"};

std::vector<std::string> shmsHeepVars = {
    "CTime.epCoinTime_ROC1", "CTime.epCoinTime_ROC2",
    "CTime.CoinTime_RAW_ROC1", "CTime.CoinTime_RAW_ROC2",
    "T.coin.hRF_tdcTime", "T.coin.pRF_tdcTime",
    "P.kin.primary.x_bj", "P.kin.primary.Q2", "P.kin.primary.nu", "P.kin.primary.W",
    "H.kin.secondary.th_xq", "H.kin.secondary.ph_xq",
    "H.kin.secondary.emiss", "H.kin.secondary.pmiss_y", "H.kin.secondary.pmiss_z",
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
  else if (runtype == "HMSHEEP")
  {
    auto vars = shmsVars;
    vars.insert(vars.end(), hmsVars.begin(), hmsVars.end());
    vars.insert(vars.end(), hmsHeepVars.begin(), hmsHeepVars.end());
    return vars;
  }
  else if (runtype == "SHMSHEEP")
  {
    auto vars = shmsVars;
    vars.insert(vars.end(), hmsVars.begin(), hmsVars.end());
    vars.insert(vars.end(), shmsHeepVars.begin(), shmsHeepVars.end());
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
    std::cout << "Invalid runtype specified! Choose from SIDIS, HMSHEEP, SHMSHEEP, SHMSDIS, HMSDIS.\n";
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
  else if (runtype == "HMSHEEP" || runtype == "SHMSHEEP")
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
    std::cout << "Invalid runtype specified! Choose from SIDIS, HMSHEEP, SHMSHEEP, SHMSDIS, HMSDIS.\n";
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
      // Phase II: use the beam energies recorded by the replay/bigtable.
      // The first period was replayed at 6.449 GeV even though the run list
      // records the later nominal setting of 6.4724 GeV.
      {{27106, 27754}, 6.4490},
      {{27756, 28106}, 8.5814},
      {{28108, 28471}, 10.6759}};

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
                           std::string runtype, // SIDIS, HMSHEEP, SHMSHEEP, SHMSDIS, HMSDIS
                           std::string indir,   // input directory containing replayed root files
                           std::string outdir   // output directory to save skimmed root files
)
{
  const std::vector<std::string> validRuntypes = {
      "SIDIS", "HMSHEEP", "SHMSHEEP", "SHMSDIS", "HMSDIS"};
  if (std::find(validRuntypes.begin(), validRuntypes.end(), runtype) == validRuntypes.end())
  {
    std::cerr << "Invalid runtype '" << runtype
              << "'. Choose SIDIS, HMSHEEP, SHMSHEEP, SHMSDIS, or HMSDIS.\n";
    if (runtype == "HEEP")
      std::cerr << "HEEP is ambiguous; use HMSHEEP or SHMSHEEP explicitly.\n";
    return;
  }

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

  ReplayParameters parameters;
  try
  {
    parameters = load_replay_parameters(run);
  }
  catch (const std::exception &error)
  {
    std::cerr << "Failed to load replay parameters for run " << run
              << ": " << error.what() << std::endl;
    return;
  }

  const bool hasHMS = runtype != "SHMSDIS";
  const bool hasSHMS = runtype != "HMSDIS";
  const bool primaryIsHMS = runtype == "SIDIS" || runtype == "HMSHEEP" || runtype == "HMSDIS";

  auto calc_dp_recon = [](double pRecon, double p, double dp)
  {
    const double scale = 1.0 + dp / 100.0;
    if (p == 0.0 || scale == 0.0)
      return std::numeric_limits<double>::quiet_NaN();
    const double pcentral = p / scale;
    return 100.0 * (pRecon / pcentral - 1.0);
  };

  if (hasHMS)
  {
    df_filtered = df_filtered
                      .Define("H_gtr_p_recon", [](double value) { return value + H_GTR_P_OFFSET; }, {"H.gtr.p"})
                      .Define("H_gtr_th_recon", [](double value) { return value + H_GTR_TH_OFFSET; }, {"H.gtr.th"})
                      .Define("H_gtr_dp_recon", calc_dp_recon, {"H_gtr_p_recon", "H.gtr.p", "H.gtr.dp"})
                      .Define("_H_lab_recon", [parameters](double pRecon, double thRecon,
                                                           double p, double th, double ph,
                                                           double px, double py, double pz)
                              { return adjusted_lab_momentum(pRecon, thRecon, p, th, ph, px, py, pz,
                                                             parameters.hOopOffset, parameters.hToLab); },
                              {"H_gtr_p_recon", "H_gtr_th_recon", "H.gtr.p", "H.gtr.th", "H.gtr.ph",
                               "H.gtr.px", "H.gtr.py", "H.gtr.pz"});
    add_if_missing(hmsVars, "H_gtr_p_recon");
    add_if_missing(hmsVars, "H_gtr_th_recon");
    add_if_missing(hmsVars, "H_gtr_dp_recon");
  }

  if (hasSHMS)
  {
    df_filtered = df_filtered
                      .Define("P_gtr_p_recon", [](double value) { return value + P_GTR_P_OFFSET; }, {"P.gtr.p"})
                      .Define("P_gtr_th_recon", [](double value) { return value + P_GTR_TH_OFFSET; }, {"P.gtr.th"})
                      .Define("P_gtr_dp_recon", calc_dp_recon, {"P_gtr_p_recon", "P.gtr.p", "P.gtr.dp"})
                      .Define("_P_lab_recon", [parameters](double pRecon, double thRecon,
                                                           double p, double th, double ph,
                                                           double px, double py, double pz)
                              { return adjusted_lab_momentum(pRecon, thRecon, p, th, ph, px, py, pz,
                                                             parameters.pOopOffset, parameters.pToLab); },
                              {"P_gtr_p_recon", "P_gtr_th_recon", "P.gtr.p", "P.gtr.th", "P.gtr.ph",
                               "P.gtr.px", "P.gtr.py", "P.gtr.pz"});
    add_if_missing(shmsVars, "P_gtr_p_recon");
    add_if_missing(shmsVars, "P_gtr_th_recon");
    add_if_missing(shmsVars, "P_gtr_dp_recon");
  }

  const std::string primaryColumn = "_primary_recon";
  const std::string primaryInputPrefix = primaryIsHMS ?
      ((runtype == "HMSDIS") ? "H.kin." : "H.kin.primary.") :
      ((runtype == "SHMSDIS") ? "P.kin." : "P.kin.primary.");
  if (primaryIsHMS)
  {
    df_filtered = df_filtered.Define(primaryColumn,
                                     [parameters](const TVector3 &momentum,
                                                  double px, double py, double pz,
                                                  double qx, double qy, double qz, double omega)
                                     { return calculate_primary(momentum, TVector3(px, py, pz),
                                                                qx, qy, qz, omega,
                                                                parameters.hPartMass, parameters.targetMass); },
                                     {"_H_lab_recon", "H.gtr.px", "H.gtr.py", "H.gtr.pz",
                                      primaryInputPrefix + "q_x", primaryInputPrefix + "q_y",
                                      primaryInputPrefix + "q_z", primaryInputPrefix + "omega"});
  }
  else
  {
    df_filtered = df_filtered.Define(primaryColumn,
                                     [parameters](const TVector3 &momentum,
                                                  double px, double py, double pz,
                                                  double qx, double qy, double qz, double omega)
                                     { return calculate_primary(momentum, TVector3(px, py, pz),
                                                                qx, qy, qz, omega,
                                                                parameters.pPartMass, parameters.targetMass); },
                                     {"_P_lab_recon", "P.gtr.px", "P.gtr.py", "P.gtr.pz",
                                      primaryInputPrefix + "q_x", primaryInputPrefix + "q_y",
                                      primaryInputPrefix + "q_z", primaryInputPrefix + "omega"});
  }

  const std::string primaryPrefix = primaryIsHMS ?
      ((runtype == "HMSDIS") ? "H_kin_" : "H_kin_primary_") :
      ((runtype == "SHMSDIS") ? "P_kin_" : "P_kin_primary_");
  const std::string xbjRecon = primaryPrefix + "x_bj_recon";
  const std::string q2Recon = primaryPrefix + "Q2_recon";
  const std::string nuRecon = primaryPrefix + "nu_recon";
  const std::string wRecon = primaryPrefix + "W_recon";
  df_filtered = df_filtered
                    .Define(xbjRecon, [](const PrimaryKinematics &value) { return value.xbj; }, {primaryColumn})
                    .Define(q2Recon, [](const PrimaryKinematics &value) { return value.Q2; }, {primaryColumn})
                    .Define(nuRecon, [](const PrimaryKinematics &value) { return value.nu; }, {primaryColumn})
                    .Define(wRecon, [](const PrimaryKinematics &value) { return value.W; }, {primaryColumn});

  std::vector<std::string> *primaryOutput = nullptr;
  if (runtype == "SIDIS") primaryOutput = &ctimeVars;
  else if (runtype == "HMSHEEP") primaryOutput = &hmsHeepVars;
  else if (runtype == "SHMSHEEP") primaryOutput = &shmsHeepVars;
  else if (runtype == "HMSDIS") primaryOutput = &hmskinVars;
  else primaryOutput = &shmskinVars;
  add_if_missing(*primaryOutput, xbjRecon);
  add_if_missing(*primaryOutput, q2Recon);
  add_if_missing(*primaryOutput, nuRecon);
  add_if_missing(*primaryOutput, wRecon);

  if (runtype == "SIDIS" || runtype == "HMSHEEP" || runtype == "SHMSHEEP")
  {
    const bool secondaryIsHMS = runtype == "SHMSHEEP";
    const std::string secondaryColumn = "_secondary_recon";
    if (secondaryIsHMS)
    {
      df_filtered = df_filtered.Define(secondaryColumn,
                                       [parameters](const PrimaryKinematics &primary, const TVector3 &momentum)
                                       { return calculate_secondary(primary, momentum, parameters.hPartMass); },
                                       {primaryColumn, "_H_lab_recon"});
    }
    else
    {
      df_filtered = df_filtered.Define(secondaryColumn,
                                       [parameters](const PrimaryKinematics &primary, const TVector3 &momentum)
                                       { return calculate_secondary(primary, momentum, parameters.pPartMass); },
                                       {primaryColumn, "_P_lab_recon"});
    }

    const std::string secondaryPrefix = secondaryIsHMS ? "H_kin_secondary_" : "P_kin_secondary_";
    const std::string thxqRecon = secondaryPrefix + "th_xq_recon";
    const std::string phxqRecon = secondaryPrefix + "ph_xq_recon";
    df_filtered = df_filtered
                      .Define(thxqRecon, [](const SecondaryKinematics &value) { return value.th_xq; }, {secondaryColumn})
                      .Define(phxqRecon, [](const SecondaryKinematics &value) { return value.ph_xq; }, {secondaryColumn});

    std::vector<std::string> *secondaryOutput = runtype == "SIDIS" ? &ctimeVars :
                                                 (runtype == "HMSHEEP" ? &hmsHeepVars : &shmsHeepVars);
    add_if_missing(*secondaryOutput, thxqRecon);
    add_if_missing(*secondaryOutput, phxqRecon);

    if (runtype == "HMSHEEP" || runtype == "SHMSHEEP")
    {
      const std::string emissRecon = secondaryPrefix + "emiss_recon";
      const std::string pmyRecon = secondaryPrefix + "pmiss_y_recon";
      const std::string pmzRecon = secondaryPrefix + "pmiss_z_recon";
      df_filtered = df_filtered
                        .Define(emissRecon, [](const SecondaryKinematics &value) { return value.emiss; }, {secondaryColumn})
                        .Define(pmyRecon, [](const SecondaryKinematics &value) { return value.pmiss_y; }, {secondaryColumn})
                        .Define(pmzRecon, [](const SecondaryKinematics &value) { return value.pmiss_z; }, {secondaryColumn});
      add_if_missing(*secondaryOutput, emissRecon);
      add_if_missing(*secondaryOutput, pmyRecon);
      add_if_missing(*secondaryOutput, pmzRecon);
    }
  }

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

    auto calc_mmass_recon = [](const PrimaryKinematics &primary,
                               const TVector3 &hadronMomentum)
    {
      ROOT::Math::PxPyPzEVector beam(0.0, 0.0, primary.beam.P(), primary.beam.P());
      ROOT::Math::PxPyPzEVector electron(primary.scattered.Px(), primary.scattered.Py(),
                                         primary.scattered.Pz(), primary.scattered.P());
      ROOT::Math::PxPyPzEVector target(0.0, 0.0, 0.0, Mp);
      ROOT::Math::PxPyPzEVector hadron(hadronMomentum.X(), hadronMomentum.Y(),
                                      hadronMomentum.Z(), hadronMomentum.Mag());
      return (beam - electron + target - hadron).M();
    };
    df_filtered = df_filtered
                      .Define("z_recon", [](double p, double nu) { return p / nu; },
                              {"P_gtr_p_recon", nuRecon})
                      .Define("pt_recon", [](double p, double theta) { return p * std::sin(theta); },
                              {"P_gtr_p_recon", "P_kin_secondary_th_xq_recon"})
                      .Define("ptx_recon", [](double ptValue, double phi) { return ptValue * std::cos(phi); },
                              {"pt_recon", "P_kin_secondary_ph_xq_recon"})
                      .Define("pty_recon", [](double ptValue, double phi) { return ptValue * std::sin(phi); },
                              {"pt_recon", "P_kin_secondary_ph_xq_recon"})
                      .Define("mmass_recon", calc_mmass_recon, {primaryColumn, "_P_lab_recon"});

    // add these new variables to ctimeVars for output
    add_if_missing(ctimeVars, "z");
    add_if_missing(ctimeVars, "pt");
    add_if_missing(ctimeVars, "ptx");
    add_if_missing(ctimeVars, "pty");
    add_if_missing(ctimeVars, "mmass");
    add_if_missing(ctimeVars, "z_recon");
    add_if_missing(ctimeVars, "pt_recon");
    add_if_missing(ctimeVars, "ptx_recon");
    add_if_missing(ctimeVars, "pty_recon");
    add_if_missing(ctimeVars, "mmass_recon");
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
