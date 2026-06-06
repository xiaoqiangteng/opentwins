package WineFermentation
  model HelloWine
    parameter Real B0 = 24.5 "Initial Brix";
    parameter Real Bf = -1.0 "Final Brix";
    parameter Real k = 0.018 "Sugar consumption rate";
    parameter Real maxAlcohol = 13.2 "Final alcohol percent";
    Real brix(start = B0, fixed = true) "Current Brix";
    Real alcohol(start = 0.0, fixed = true) "Estimated alcohol percent";
    Real progress "Fermentation progress, 0 to 100";
  equation
    der(brix) = -k * max(brix - Bf, 0.0);
    alcohol = maxAlcohol * min(max((B0 - brix) / (B0 - Bf), 0.0), 1.0);
    progress = 100.0 * min(max((B0 - brix) / (B0 - Bf), 0.0), 1.0);
  end HelloWine;

  model ContinuationFermentation
    parameter Real initialBrixReference = 24.5 "Original initial Brix of this batch";
    parameter Real finalBrix = -1.0 "Expected final Brix";
    parameter Real brixStart = 16.0 "Current Brix at simulation start";
    parameter Real alcoholStart = 4.0 "Current alcohol at simulation start";
    parameter Real co2Start = 3000.0 "Current CO2 at simulation start";
    parameter Real yeastStart = 0.6 "Current yeast activity index";
    parameter Real temperatureSet = 25.0 "Assumed fermentation temperature";
    parameter Real optimalTemperature = 25.0 "Optimal temperature";
    parameter Real warningTemperature = 30.0 "Warning threshold";
    parameter Real criticalTemperature = 33.0 "Critical threshold";
    parameter Real kSugar = 0.018 "Sugar consumption coefficient";
    parameter Real yAlcohol = 0.55 "Alcohol yield coefficient";
    parameter Real yCO2 = 260.0 "CO2 yield coefficient";
    parameter Real kCO2 = 0.10 "CO2 dissipation coefficient";
    parameter Real co2Base = 420.0 "Atmospheric CO2 baseline";
    parameter Real alphaT = 0.018 "Temperature sensitivity";
    parameter Real mu = 0.025 "Yeast growth rate";
    parameter Real deathRate = 0.004 "Yeast death rate";
    parameter Real yeastMax = 1.0 "Maximum yeast activity";
    Real brix(start = brixStart, fixed = true);
    Real alcohol(start = alcoholStart, fixed = true);
    Real co2(start = co2Start, fixed = true);
    Real yeast(start = yeastStart, fixed = true);
    Real temperature;
    Real fermentationRate;
    Real tempFactor;
    Real progress;
    Real qualityScore;
    Real riskCode;
  equation
    temperature = temperatureSet;
    tempFactor = exp(-alphaT * (temperature - optimalTemperature)^2);
    fermentationRate = kSugar * max(yeast, 0.0) * tempFactor * max(brix - finalBrix, 0.0);
    der(brix) = -fermentationRate;
    der(alcohol) = yAlcohol * fermentationRate;
    der(co2) = yCO2 * fermentationRate - kCO2 * max(co2 - co2Base, 0.0);
    der(yeast) = mu * yeast * (1.0 - yeast / yeastMax) * tempFactor - deathRate * yeast;
    progress = 100.0 * min(max((initialBrixReference - brix) / (initialBrixReference - finalBrix), 0.0), 1.0);
    riskCode = if progress >= 98.0 then 3.0
               else if temperature > criticalTemperature then 2.0
               else if temperature > warningTemperature then 1.0
               else 0.0;
    qualityScore = max(0.0, min(100.0,
      100.0
      - (if temperature > warningTemperature then 18.0 else 0.0)
      - (if temperature > criticalTemperature then 14.0 else 0.0)
      - (if progress < 20.0 and time > 24.0 then 5.0 else 0.0)
    ));
  end ContinuationFermentation;
end WineFermentation;
