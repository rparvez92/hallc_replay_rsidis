#include <TBranch.h>
#include <TFile.h>
#include <TSystem.h>
#include <TTree.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct RunInfo {
  Long64_t run;
  std::string runType;
  std::string replayMode;
};

struct ScalerResult {
  bool applicable = false;
  bool valid = false;
  Long64_t eventNumber = 0;
  Long64_t difference = 0;
  bool flagged = false;
  std::string error;
};

std::vector<std::string> SplitCsv(const std::string& line) {
  std::vector<std::string> fields;
  std::stringstream stream(line);
  std::string field;
  while (std::getline(stream, field, ',')) fields.push_back(field);
  return fields;
}

std::string CsvQuote(const std::string& value) {
  if (value.find_first_of(",\"\n\r") == std::string::npos) return value;
  std::string escaped = "\"";
  for (char c : value) {
    if (c == '\"') escaped += '\"';
    escaped += c;
  }
  return escaped + "\"";
}

std::vector<RunInfo> ReadRunList(const char* path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error(std::string("cannot open run list: ") + path);

  std::vector<RunInfo> runs;
  std::string line;
  std::getline(input, line);  // header
  while (std::getline(input, line)) {
    if (line.empty()) continue;
    const auto fields = SplitCsv(line);
    if (fields.size() != 3) throw std::runtime_error("malformed run-list row: " + line);
    char* end = nullptr;
    const Long64_t run = std::strtoll(fields[0].c_str(), &end, 10);
    if (!end || *end != '\0') throw std::runtime_error("invalid run number: " + fields[0]);
    runs.push_back({run, fields[1], fields[2]});
  }
  return runs;
}

std::string FileName(const RunInfo& info) {
  if (info.replayMode == "coin") return "coin_replay_production_" + std::to_string(info.run) + "_-1.root";
  if (info.replayMode == "hms") return "hms_coin_replay_production_" + std::to_string(info.run) + "_-1.root";
  if (info.replayMode == "shms") return "shms_coin_replay_production_" + std::to_string(info.run) + "_-1.root";
  throw std::runtime_error("unsupported replay mode: " + info.replayMode);
}

ScalerResult CheckScaler(TTree* tree, const char* treeName, Long64_t physicsEntries,
                         Long64_t threshold, bool applicable) {
  ScalerResult result;
  result.applicable = applicable;
  if (!applicable) return result;
  if (!tree) {
    result.error = std::string("MISSING_") + treeName;
    return result;
  }
  if (tree->GetEntries() <= 0) {
    result.error = std::string("EMPTY_") + treeName;
    return result;
  }
  TBranch* branch = tree->GetBranch("evNumber");
  if (!branch) {
    result.error = std::string("MISSING_") + treeName + "_EVNUMBER";
    return result;
  }

  Double_t value = std::numeric_limits<Double_t>::quiet_NaN();
  tree->SetBranchStatus("*", 0);
  tree->SetBranchStatus("evNumber", 1);
  if (tree->SetBranchAddress("evNumber", &value) < 0 ||
      tree->GetEntry(tree->GetEntries() - 1) <= 0) {
    result.error = std::string("READ_ERROR_") + treeName + "_EVNUMBER";
    tree->ResetBranchAddresses();
    tree->SetBranchStatus("*", 1);
    return result;
  }
  tree->ResetBranchAddresses();
  tree->SetBranchStatus("*", 1);

  const double rounded = std::round(value);
  if (!std::isfinite(value) || std::fabs(value - rounded) > 1e-6 ||
      rounded < static_cast<double>(std::numeric_limits<Long64_t>::min()) ||
      rounded > static_cast<double>(std::numeric_limits<Long64_t>::max())) {
    result.error = std::string("INVALID_") + treeName + "_EVNUMBER";
    return result;
  }

  result.valid = true;
  result.eventNumber = static_cast<Long64_t>(rounded);
  result.difference = result.eventNumber - physicsEntries;
  result.flagged = std::llabs(result.difference) >= threshold;
  return result;
}

std::string ValueOrBlank(const ScalerResult& result, Long64_t value) {
  return result.valid ? std::to_string(value) : "";
}

std::string FlagOrBlank(const ScalerResult& result) {
  return result.applicable && result.valid ? (result.flagged ? "1" : "0") : "";
}

std::string JoinErrors(const std::vector<std::string>& errors) {
  std::string joined;
  for (const auto& error : errors) {
    if (error.empty()) continue;
    if (!joined.empty()) joined += ";";
    joined += error;
  }
  return joined;
}

}  // namespace

void check_scaler_event_batch(const char* phase,
                              const char* runListPath,
                              const char* rootDirectory,
                              const char* outputCsv,
                              Long64_t startRow = 0,
                              Long64_t batchSize = 50,
                              Long64_t threshold = 10) {
  if (startRow < 0 || batchSize <= 0 || threshold < 0)
    throw std::invalid_argument("startRow must be >= 0, batchSize > 0, and threshold >= 0");

  const auto runs = ReadRunList(runListPath);
  const Long64_t stop = std::min<Long64_t>(runs.size(), startRow + batchSize);
  if (startRow >= static_cast<Long64_t>(runs.size()))
    throw std::out_of_range("startRow is beyond the run list");

  std::ofstream output(outputCsv);
  if (!output) throw std::runtime_error(std::string("cannot create output CSV: ") + outputCsv);
  output << "phase,run,run_type,replay_mode,root_file,t_entries,"
            "tsh_last_evnumber,tsh_difference,tsh_flag,"
            "tsp_last_evnumber,tsp_difference,tsp_flag,overall_flag,status\n";

  Long64_t flaggedCount = 0;
  Long64_t errorCount = 0;
  std::string rootDir(rootDirectory);
  if (!rootDir.empty() && rootDir.back() != '/') rootDir += '/';

  for (Long64_t index = startRow; index < stop; ++index) {
    const auto& info = runs[index];
    const std::string rootFile = rootDir + FileName(info);
    const bool useHms = info.replayMode == "coin" || info.replayMode == "hms";
    const bool useShms = info.replayMode == "coin" || info.replayMode == "shms";
    Long64_t physicsEntries = -1;
    ScalerResult hms;
    ScalerResult shms;
    hms.applicable = useHms;
    shms.applicable = useShms;
    std::vector<std::string> errors;

    TFile* file = nullptr;
    if (gSystem->AccessPathName(rootFile.c_str(), kReadPermission)) {
      errors.push_back("MISSING_FILE");
    } else {
      file = TFile::Open(rootFile.c_str(), "READ");
    }
    if (file && file->IsZombie()) {
      errors.push_back("UNREADABLE_FILE");
      file->Close();
      delete file;
      file = nullptr;
    }
    if (!file) {
      if (errors.empty()) errors.push_back("UNREADABLE_FILE");
    } else {
      TTree* physics = dynamic_cast<TTree*>(file->Get("T"));
      if (!physics) {
        errors.push_back("MISSING_T");
      } else if (physics->GetEntries() <= 0) {
        errors.push_back("EMPTY_T");
      } else {
        physicsEntries = physics->GetEntries();
        hms = CheckScaler(dynamic_cast<TTree*>(file->Get("TSH")), "TSH", physicsEntries, threshold, useHms);
        shms = CheckScaler(dynamic_cast<TTree*>(file->Get("TSP")), "TSP", physicsEntries, threshold, useShms);
        errors.push_back(hms.error);
        errors.push_back(shms.error);
      }
      file->Close();
      delete file;
    }

    const bool overallFlag = (hms.valid && hms.flagged) || (shms.valid && shms.flagged);
    const std::string errorStatus = JoinErrors(errors);
    const std::string status = !errorStatus.empty() ? errorStatus : (overallFlag ? "DISCREPANCY" : "OK");
    flaggedCount += overallFlag ? 1 : 0;
    errorCount += !errorStatus.empty() ? 1 : 0;

    output << CsvQuote(phase) << ',' << info.run << ',' << CsvQuote(info.runType) << ','
           << CsvQuote(info.replayMode) << ',' << CsvQuote(rootFile) << ','
           << (physicsEntries >= 0 ? std::to_string(physicsEntries) : "") << ','
           << ValueOrBlank(hms, hms.eventNumber) << ',' << ValueOrBlank(hms, hms.difference) << ','
           << FlagOrBlank(hms) << ',' << ValueOrBlank(shms, shms.eventNumber) << ','
           << ValueOrBlank(shms, shms.difference) << ',' << FlagOrBlank(shms) << ','
           << (overallFlag ? "1" : "0") << ',' << CsvQuote(status) << '\n';
  }

  std::cout << phase << " rows " << startRow << "-" << (stop - 1)
            << ": checked=" << (stop - startRow) << ", flagged=" << flaggedCount
            << ", errors=" << errorCount << ", output=" << outputCsv << std::endl;
}
