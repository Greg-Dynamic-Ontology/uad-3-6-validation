# Constraint loader backlog

Source: C:\Users\grego\projects\uad-3-6-validation\specs\fannie-mae\Appendix H-1 UAD Compliance Rules - URAR v1.5.xlsm
Worksheet: UAD Compliance Rules v1.5

Workbook rows: 728. Loaded: 548. Omitted: 180.

Prior inventory categories (not a new semantic classification):

- other_conditional_scoped: 167
- alternative_mutually_exclusive: 13

Category assignments are prior inventory classifications.
A rule ID appearing in test code is only a reference, not proof of behavioral
coverage or a passing test.

## Omitted rows

### UAD1026 — PropertyGroundLeaseRenewableIndicator

Category: other_conditional_scoped

Rule logic: If PropertyEstateType = "Leasehold" and LandOwnedInCommonIndicator =
"false", and PropertyGroundLeaseRenewableIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1039 — ValuationCommentText

Category: other_conditional_scoped

Rule logic: If SpecialTaxAssessmentsIndicator = "true" and ValuationCommentText is not provided in the instance of VALUATION_COMMENTARY with ValuationAnalysisCategoryType = "PropertySpecialTaxAssessments"

Test-code references: None found in top-level Python test files.

### UAD1043 — ParcelsLegalDescription

Category: alternative_mutually_exclusive

Rule logic: If ImageCategoryType = "LegalDescription" is not provided in any instance of IMAGE, and ParcelsLegalDescription is not provided

Test-code references: None found in top-level Python test files.

### UAD1073 — RoofEstimatedAgeRangeType

Category: other_conditional_scoped

Rule logic: If ImprovementComponentType = "Roof" and RoofEstimatedAgeRangeType is not provided in ROOF_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1074 — RoofObservableIndicator

Category: other_conditional_scoped

Rule logic: If ImprovementComponentType = "Roof" and RoofObservableIndicator is not provided in ROOF_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1078 — ImprovementComponentConditionStatusType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ImprovementComponentType <> "Roof"), or (ImprovementType = "Dwelling" and ImprovementComponentType = "Roof" and RoofObservableIndicator = "true"), and ImprovementComponentConditionStatusType is not provided in a given instance of STRUCTURE_COMPONENT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1084 — LivingUnitCount

Category: other_conditional_scoped

Rule logic: If ImprovementType = "Dwelling" or 
(ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true"), and LivingUnitCount is not provided in a given instance of STRUCTURE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1087 — StoriesCount

Category: other_conditional_scoped

Rule logic: If StructuralDesignType = "Highrise" or "Midrise", and StoriesCount is not provided in a given instance of STRUCTURE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1099 — FrontDoorApproximateElevationRangeType

Category: other_conditional_scoped

Rule logic: If FrontDoorApproximateElevationRangeType is not provided in STRUCTURE_DETAIL for a given instance of IMRPOVEMENT with ImprovementType = "Dwelling"

Test-code references: None found in top-level Python test files.

### UAD1103 — ManufacturedHomeAttachedToFoundationIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured") or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome"), and ManufacturedHomeAttachedToFoundationIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1104 — ManufacturedHomeHitchWheelsAxlesRemovedIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured") or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0), and ManufacturedHomeHitchWheelsAxlesRemovedIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1105 — ManufacturedHomeHUDCertificateLabelIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured") or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0), and ManufacturedHomeHUDCertificateLabelIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1106 — ManufacturedHomeHUDDataPlateAttachedIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured") or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0), and ManufacturedHomeHUDDataPlateAttachedIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1108 — ManufacturedHomeInvoiceReasonableIndicator

Category: other_conditional_scoped

Rule logic: If ImprovementType = "Dwelling" and ConstructionMethod = "Manufactured" and (ManufacturedHomeRetailerInvoiceReviewedIndicator = "true" or ManufacturedHomeInvoiceReviewedIndicator = "true") and ManufacturedHomeInvoiceReasonableIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1113 — ManufacturedHomeModificationIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured") or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0), and ManufacturedHomeModificationIndicator is not provided in a given instance of MANUFACTURED_HOME_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1139 — BelowGradeExteriorAccessType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and (AccessType = "ExteriorAccessOnly" or "InteriorAndExteriorAccess")) or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true" and (AccessType = "ExteriorAccessOnly" or "InteriorAndExteriorAccess")), and BelowGradeExteriorAccessType is not provided in a given instance of LEVEL

Test-code references: None found in top-level Python test files.

### UAD1141 — GradeLevelType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and GradeLevelType is not provided in a given instance of LEVEL

Test-code references: None found in top-level Python test files.

### UAD1145 — RoomConditionStatusType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true") and (RoomType = "FullBathroom" or "HalfBathroom" or "Kitchen"), and RoomConditionStatusType is not provided in a given instance of ROOM_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1146 — RoomUpdateStatusType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and RoomType = ("FullBathroom" or "HalfBathroom" or "Kitchen"), and RoomUpdateStatusType is not provided in a given instance of ROOM_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1148 — ImprovementComponentType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and ImprovementComponentType is not provided in a given instance of INTERIOR_COMPONENT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1149 — ImprovementComponentType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and ImprovementComponentType = "Flooring" is not provided in INTERIOR_COMPONENT_DETAIL for a given instance of PROPERTY_UNIT

Test-code references: None found in top-level Python test files.

### UAD1152 — ImprovementComponentType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and ImprovementComponentType = "WallsAndCeiling" is not provided in INTERIOR_COMPONENT_DETAIL in a given instance of PROPERTY_UNIT

Test-code references: None found in top-level Python test files.

### UAD1157 — CornerUnitIndicator

Category: other_conditional_scoped

Rule logic: If StructuralDesignType = "Lowrise" or "Highrise" or "Midrise", and CornerUnitIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1158 — FloorIdentifier

Category: other_conditional_scoped

Rule logic: If ImprovementType = "Dwelling" and AttachmentType = "Attached" and StructuralDesignType = ("Lowrise" or "Highrise" or "Midrise"), and FloorIdentifier is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1159 — UnitIncludedInRentScheduleIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" and RentScheduleIndicator = "true") or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true" and RentScheduleIndicator = "true") , and UnitIncludedInRentScheduleIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1160 — InteriorConditionRatingCode

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") 
or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1161 — InteriorQualityRatingCode

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling") 
OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1162 — UtilitiesMeteredSeparatelyIndicator

Category: other_conditional_scoped

Rule logic: If (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0), and UtilitiesMeteredSeparatelyIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1164 — AccessoryDwellingUnitIndicator

Category: other_conditional_scoped

Rule logic: if AccessoryDwellingUnitIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL when STRUCTURE_DETAIL/LivingUnitCount > 0

Test-code references: None found in top-level Python test files.

### UAD1169 — ImprovementComponentConditionStatusType

Category: other_conditional_scoped

Rule logic: If ImprovementComponentType = "Flooring" and ImprovementComponentConditionStatusType is not provided in FLOOR_COVERING in a given instance of PROPERTY_UNIT

Test-code references: None found in top-level Python test files.

### UAD1170 — UnitIdentifier

Category: other_conditional_scoped

Rule logic: If (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0), and UnitIdentifier is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1173 — OverallBathroomsUpdateStatusType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and OverallBathroomsUpdateStatusType is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1174 — BedroomCount

Category: other_conditional_scoped

Rule logic: If ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and BedroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1175 — FullBathroomCount

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and FullBathroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1176 — HalfBathroomCount

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and HalfBathroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1177 — LevelType

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and LevelType is not provided in a given instance ROOM_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1184 — LevelFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and LevelFinishedAreaMeasure is not provided in a given instance of LEVEL

Test-code references: None found in top-level Python test files.

### UAD1185 — LevelUnfinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and LevelUnfinishedAreaMeasure is not provided in a given instance of LEVEL

Test-code references: None found in top-level Python test files.

### UAD1186 — UnitStandardAboveGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitStandardAboveGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1187 — UnitNonStandardAboveGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitNonStandardAboveGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1188 — UnitAboveGradeUnfinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitAboveGradeUnfinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1189 — UnitStandardBelowGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitStandardBelowGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1190 — UnitBelowGradeUnfinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitBelowGradeUnfinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1193 — SaleType

Category: other_conditional_scoped

Rule logic: If PriorSalesOrTransfersIndicator = "true" and OwnershipTransferTransactionType = "Sale", and SaleType is not provided in a given instance of SALES_HISTORY

Test-code references: None found in top-level Python test files.

### UAD1221 — InspectionDate

Category: other_conditional_scoped

Rule logic: If PropertyDataReportIndicator = "true" and InspectionDate is not provided in SERVICE container with ServiceType = "Inspection"

Test-code references: None found in top-level Python test files.

### UAD1228 — DepreciatedCostOutbuildingsTotalAmount

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true" and DepreciatedCostOutbuildingsTotalAmount is not provided when there are one or more instances of IMPROVEMENT_DETAIL with ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true"

Test-code references: None found in top-level Python test files.

### UAD1229 — SiteEstimatedValueAmount

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true", or 
(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteEstimatedValueAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1231 — SiteValuationMethodType

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true", or 
(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteValuationMethodType is not provided

Test-code references: None found in top-level Python test files.

### UAD1237 — DepreciationTotalAmount

Category: alternative_mutually_exclusive

Rule logic: If DepreciationTotalAmount is provided, and (any of DepreciationExternalAmount, DepreciationFunctionalAmount, and DepreciationPhysicalAmount are also provided) in a given instance of IMPROVEMENT_COST_AND_DEPRECIATED_VALUE/IMPROVEMENT_DEPRECIATION

Test-code references: None found in top-level Python test files.

### UAD1239 — DataSourceEffectiveDate

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true", and (DataSourceType = "BuilderOrDeveloper" or "CostService" or "CostSurvey" or "Other"), and DataSourceEffectiveDate is not provided in the instance of DATA_SOURCE that is related to cost approach

Test-code references: None found in top-level Python test files.

### UAD1240 — DataSourceName

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true", and DataSourceType = "CostService", and DataSourceName is not provided in a given instance of DATA_SOURCE

Test-code references: None found in top-level Python test files.

### UAD1241 — DataSourceQualityRatingCode

Category: other_conditional_scoped

Rule logic: If CostApproachIndicator = "true" and DataSourceQualityRatingCode is not provided in the instance of DATA_SOURCE with DataSourceType = "CostService"

Test-code references: None found in top-level Python test files.

### UAD1251 — OwnershipTransferTransactionAmount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "GrossRentMultiplierComparable" and OwnershipTransferTransactionType = "Sale" and OwnershipTransferTransactionAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1267 — PropertyAsIsConditionRatingCode

Category: other_conditional_scoped

Rule logic: If NewConstructionIndicator = "false" and (PropertyValuationConditionalConclusionType = "SubjectToCompletionPerPlans" or "SubjectToRepair") and PropertyAsIsConditionRatingCode is not provided

Test-code references: None found in top-level Python test files.

### UAD1282 — MIMETypeIdentifier

Category: other_conditional_scoped

Rule logic: If @ValuationUseType="GrossRentMultiplierComparable" and MIMETypeIdentifier is not provided in a given instance of IMAGE

Test-code references: None found in top-level Python test files.

### UAD1301 — ParcelAreaMeasure

Category: other_conditional_scoped

Rule logic: If LandOwnedInCommonIndicator = "false", and (ParcelDescriptionClassificationType = "VacantLand" or "LandWithDwelling" or "LandWithImprovement"), and ParcelAreaMeasure is not provided in a given instance of PARCEL_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1306 — CommunityLandTrustIndicator

Category: other_conditional_scoped

Rule logic: If PropertyEstateType = "Leasehold" or "Other", and CommunityLandTrustIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1307 — NonResidentialModificationIndicator

Category: other_conditional_scoped

Rule logic: If LandOwnedInCommonIndicator = "false", and PropertyMixedUsageIndicator = "true", and NonResidentialModificationIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1309 — PropertyPrimarilyResidentialUseIndicator

Category: other_conditional_scoped

Rule logic: If LandOwnedInCommonIndicator = "false", and PropertyMixedUsageIndicator = "true", and PropertyPrimarilyResidentialUseIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1333 — WaterAccessRightType

Category: other_conditional_scoped

Rule logic: If SiteInfluenceType = "BodyOfWater" and PrivateAccessIndicator = "true", and WaterAccessRightType is not provided in a given instance of BODY_OF_WATER

Test-code references: None found in top-level Python test files.

### UAD1337 — WaterAccessDepthType

Category: other_conditional_scoped

Rule logic: If SiteInfluenceType = "BodyOfWater" and PrivateAccessIndicator = "true", and WaterAccessDepthType is not provided in a given instance of BODY_OF_WATER

Test-code references: None found in top-level Python test files.

### UAD1339 — WaterFrontageTotalLengthLinearMeasure

Category: other_conditional_scoped

Rule logic: If PrivateAccessIndicator = "true" for one or more instances of BODY_OF_WATER and WaterFrontageTotalLengthLinearMeasure is not provided in a given instance of SITE_INFLUENCE_DETAIL with SiteInfluenceType = "BodyOfWater"

Test-code references: None found in top-level Python test files.

### UAD1340 — WaterfrontDevelopmentRightsIndicator

Category: other_conditional_scoped

Rule logic: If WaterfrontFeatureType = "None" and WaterfrontDevelopmentRightsIndicator is not provided in a given instance of SITE_INFLUENCE_DETAIL with SiteInfluenceType = "BodyOfWater"

Test-code references: None found in top-level Python test files.

### UAD1343 — ParcelsContiguousIndicator

Category: other_conditional_scoped

Rule logic: If LandOwnedInCommonIndicator = "false", and ParcelCount > 1, and ParcelsContiguousIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1367 — SiteZoningClassificationIdentifier

Category: other_conditional_scoped

Rule logic: If SiteZoningComplianceType <> "NoZoning" and SiteZoningClassificationIdentifier is not provided

Test-code references: None found in top-level Python test files.

### UAD1368 — SiteZoningClassificationDescription

Category: other_conditional_scoped

Rule logic: If SiteZoningComplianceType <> "NoZoning" and SiteZoningClassificationDescription is not provided

Test-code references: None found in top-level Python test files.

### UAD1387 — ValuationCommentText

Category: other_conditional_scoped

Rule logic: If ValuationCommentText is not provided in the instance of VALUATION_COMMENTARY with ValuationAnalysisCategoryType = "OverallQualityAndCondition"

Test-code references: None found in top-level Python test files.

### UAD1394 — MortgageType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and NoFinancingTransactionIndicator = "false" and MortgageType is not provided

Test-code references: None found in top-level Python test files.

### UAD1395 — MortgageTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and MortgageType = "Other", and MortgageTypeOtherDescription is not provided

Test-code references: None found in top-level Python test files.

### UAD1397 — ComparableToSubjectDirectionType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ProximityToSubjectDistanceLinearMeasure > 0, and ComparableToSubjectDirectionType is not provided

Test-code references: None found in top-level Python test files.

### UAD1399 — RestrictionTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and RestrictionType = "Other" and RestrictionTypeOtherDescription is not provided in a given instance of CONDITION_COVENANT_RESTRICTION

Test-code references: None found in top-level Python test files.

### UAD1401 — EasementTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and EasementType = "Other" and EasementTypeOtherDescription is not provided in a given instance of EASEMENT

Test-code references: None found in top-level Python test files.

### UAD1407 — CarStorageTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and CarStorageType = "Other" and CarStorageTypeOtherDescription is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1408 — CarStorageAttachmentType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and CarStorageType = "Garage" or "Carport", and CarStorageAttachmentType is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1409 — ImprovedSurfaceMaterialType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and CarStorageType = "Driveway" or "SharedDriveway", and ImprovedSurfaceMaterialType is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1410 — ImprovedSurfaceMaterialTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ImprovedSurfaceMaterialType = "Other" and ImprovedSurfaceMaterialTypeOtherDescription is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1411 — ParkingSpacesCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (CarStorageType = "Driveway" or "SharedDriveway" and TenOrMoreParkingSpacesIndicator = "false") or (CarStorageType = "Carport" or "CommonCarport" or "Garage" or "OpenLot" or "Other" or "ParkingGarage"), and ParkingSpacesCount is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1412 — ProjectParkingSpaceAssignmentType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable", and CarStorageType = "CommonCarport" or "OpenLot" or "ParkingGarage", and ProjectParkingSpaceAssignmentType is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1414 — TenOrMoreParkingSpacesIndicator

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable", and CarStorageType = "Driveway" or "SharedDriveway", and TenOrMoreParkingSpacesIndicator is not provided in a given instance of CAR_STORAGE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1416 — PropertyStructureBuiltYear

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ImprovementType = "Dwelling" and PropertyStructureBuiltYear is not provided in a given instance of IMPROVEMENT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1419 — InteriorConditionRatingCode

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" 
or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1420 — InteriorQualityRatingCode

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" 
OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1422 — HeatingSystemTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and HeatingSystemType = "Other" and HeatingSystemTypeOtherDescription is not provided in a given instance of HEATING_SYSTEM

Test-code references: None found in top-level Python test files.

### UAD1423 — StructuralDesignType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ImprovementType = "Dwelling" and AttachmentType = "Attached" and StructuralDesignType is not provided in a given instance of ARCHITECTURAL_DESIGN

Test-code references: None found in top-level Python test files.

### UAD1424 — StructuralDesignTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and StructuralDesignType = "Other" and StructuralDesignTypeOtherDescription is not provided in a given instance of ARCHITECTURAL_DESIGN

Test-code references: None found in top-level Python test files.

### UAD1425 — TotalFinishedAreaOfAllLivingUnitsIncludingADUAreaMeasure

Category: other_conditional_scoped

Rule logic: If SalesComparisonApproachIndicator = "true" and LivingUnitExcludingADUCount > 1 and TotalFinishedAreaOfAllLivingUnitsIncludingADUAreaMeasure is not provided

Test-code references: None found in top-level Python test files.

### UAD1426 — ExteriorConditionRatingCode

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType = "SalesComparable" and ImprovementType = "Dwelling" and HomeownerResponsibleForExteriorMaintenanceIndicator = "true"), and (@ValuationUseType = "SubjectProperty" and HomeownerResponsibleForExteriorMaintenanceIndicator = "true") and ExteriorConditionRatingCode is not provided in a given instance of STRUCTURE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1427 — ExteriorQualityRatingCode

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType = "SalesComparable" and ImprovementType = "Dwelling" and HomeownerResponsibleForExteriorMaintenanceIndicator = "true"), and (@ValuationUseType = "SubjectProperty" and HomeownerResponsibleForExteriorMaintenanceIndicator = "true") and ExteriorQualityRatingCode is not provided in a given instance of STRUCTURE_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1439 — OwnershipTransferTransactionAmount

Category: alternative_mutually_exclusive

Rule logic: If @ValuationUseType = "SalesComparable" and (OwnershipTransferTransactionAmount and OwnershipTransferAmountNotAvailableReasonType) is not provided in a given instance of SALES_HISTORY

Test-code references: None found in top-level Python test files.

### UAD1440 — OwnershipTransferAmountNotAvailableReasonTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and OwnershipTransferAmountNotAvailableReasonType = "Other" and OwnershipTransferAmountNotAvailableReasonTypeOtherDescription is not provided in a given instance of SALES_HISTORY

Test-code references: None found in top-level Python test files.

### UAD1444 — SaleTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and SaleType = "Other" and SaleTypeOtherDescription is not provided in a given instance of SALES_HISTORY

Test-code references: None found in top-level Python test files.

### UAD1446 — HazardZoneTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and HazardZoneType = "Other" and HazardZoneTypeOtherDescription is not provided in a given instance of HAZARD_ZONE

Test-code references: None found in top-level Python test files.

### UAD1447 — ImprovedSurfaceMaterialTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ImprovedSurfaceMaterialType = "Other", and ImprovedSurfaceMaterialTypeOtherDescription is not provided in a given instance of ACCESS_STREET

Test-code references: None found in top-level Python test files.

### UAD1448 — SiteDrainageReasonTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and SiteDrainageReasonType = "Other" and SiteDrainageReasonTypeOtherDescription is not provided in a given instance of DRAINAGE_IMPACT_REASON

Test-code references: None found in top-level Python test files.

### UAD1449 — LotSizeAreaMeasure

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and LandOwnedInCommonIndicator = "false" and LotSizeAreaMeasure is not provided

Test-code references: None found in top-level Python test files.

### UAD1451 — ViewTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ViewType = "Other" and ViewTypeOtherDescription is not provided in a given instance of SITE_VIEW

Test-code references: None found in top-level Python test files.

### UAD1453 — AccessoryDwellingUnitIndicator

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and LivingUnitCount > 0, and AccessoryDwellingUnitIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1457 — AdjustedSalesPricePerBedroomAmount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and LivingUnitExcludingADUCount > 1 and AdjustedSalesPricePerBedroomAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1458 — AdjustedSalesPricePerUnitAmount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and LivingUnitExcludingADUCount > 1, and AdjustedSalesPricePerUnitAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1462 — WaterAccessDepthTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and WaterAccessDepthType = "Other" and WaterAccessDepthTypeOtherDescription is not provided in a given instance of BODY_OF_WATER

Test-code references: None found in top-level Python test files.

### UAD1463 — BedroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" AND OutbuildingRealPropertyIndicator = "true" AND AccessoryDwellingUnitIndicator = "true")), and BedroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1464 — FullBathroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" AND OutbuildingRealPropertyIndicator = "true" AND AccessoryDwellingUnitIndicator = "true")), and FullBathroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1465 — HalfBathroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" AND OutbuildingRealPropertyIndicator = "true" AND AccessoryDwellingUnitIndicator = "true")), and HalfBathroomCount is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1467 — TotalFinishedAreaOfAllLivingUnitsIncludingADUAreaMeasure

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType = "SalesComparable") and (@ValuationUseType = "SubjectProperty" and LivingUnitExcludingADUCount > 1), and TotalFinishedAreaOfAllLivingUnitsIncludingADUAreaMeasure is not provided

Test-code references: None found in top-level Python test files.

### UAD1468 — DataSourceIdentifier

Category: other_conditional_scoped

Rule logic: If DataSourceIdentifier is not provided in a given instance of DATA_SOURCE with DataSourceType = "MLS" that has arc role to PROPERTY container with @ValuationUseType <> ("SubjectProperty" or "PropertyAnalyzedNotUsed")

Test-code references: None found in top-level Python test files.

### UAD1469 — NativeAmericanLandsTypeOtherDescription

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and NativeAmericanLandsType = "Other" and NativeAmericanLandsTypeOtherDescription is not provided

Test-code references: None found in top-level Python test files.

### UAD1476 — LavaFlowZoneCode

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and HazardZoneType = "USGSLavaFlowZone", and LavaFlowZoneCode is not provided

Test-code references: None found in top-level Python test files.

### UAD1478 — ProjectLegalStructureType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and PropertyInProjectIndicator = "true" and ProjectLegalStructureType is not provided

Test-code references: None found in top-level Python test files.

### UAD1481 — ContractDateUnknownIndicator

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ListingStatusType = "Pending" or "SettledSale" and ContractDateUnknownIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1482 — UnitStandardAboveGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitStandardAboveGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1483 — UnitStandardBelowGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitStandardBelowGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1484 — UnitNonStandardBelowGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and UnitNonStandardBelowGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1487 — UnitTotalFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and UnitTotalFinishedAreaMeasure is not provided in PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1488 — TotalMonthlyActualRentAmount

Category: other_conditional_scoped

Rule logic: If (RentScheduleIndicator = "true" or IncomeApproachIndicator = "true"), and TotalMonthlyActualRentAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1489 — TotalMonthlyMarketRentAmount

Category: other_conditional_scoped

Rule logic: If (RentScheduleIndicator = "true" or IncomeApproachIndicator = "true"), and TotalMonthlyMarketRentAmount is not provided

Test-code references: None found in top-level Python test files.

### UAD1490 — UnitMonthlyActualRentAmount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and UnitMonthlyActualRentAmount is not provided in UNIT_RENT_SCHEDULE

Test-code references: None found in top-level Python test files.

### UAD1491 — UnitTotalFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If RentScheduleIndicator = "true", and UnitIncludedInRentScheduleIndicator = "true", and UnitTotalFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1492 — ComparableToSubjectDirectionType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and ProximityToSubjectDistanceLinearMeasure > 0, and ComparableToSubjectDirectionType is not provided

Test-code references: None found in top-level Python test files.

### UAD1496 — RentControlStatusType

Category: other_conditional_scoped

Rule logic: If RentScheduleIndicator = "true", and UnitIncludedInRentScheduleIndicator = "true", and RentControlStatusType is not provided in a given instance of UNIT_RENT_SCHEDULE

Test-code references: None found in top-level Python test files.

### UAD1497 — UnitMonthlyActualRentAmount

Category: other_conditional_scoped

Rule logic: If RentScheduleIndicator = "true", and UnitIncludedInRentScheduleIndicator = "true", and UnitMonthlyActualRentAmount is not provided in a given instance of UNIT_RENT_SCHEDULE

Test-code references: None found in top-level Python test files.

### UAD1498 — UnitMonthlyMarketRentAmount

Category: other_conditional_scoped

Rule logic: If RentScheduleIndicator = "true", and UnitIncludedInRentScheduleIndicator = "true", and UnitMonthlyMarketRentAmount is not provided in a given instance of UNIT_RENT_SCHEDULE

Test-code references: None found in top-level Python test files.

### UAD1499 — BedroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and BedroomCount is not provided in PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1500 — FullBathroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and FullBathroomCount is not provided in PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1501 — HalfBathroomCount

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "RentalComparable" and HalfBathroomCount is not provided in PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1521 — PropertyExteriorInspectionMethodType

Category: other_conditional_scoped

Rule logic: If PropertyDataReportIndicator = "true" and PropertyExteriorInspectionMethodType is not provided in SERVICE container with ServiceType = "Inspection"

Test-code references: None found in top-level Python test files.

### UAD1522 — PropertyInteriorInspectionMethodType

Category: other_conditional_scoped

Rule logic: If PropertyDataReportIndicator = "true" and PropertyInteriorInspectionMethodType is not provided in SERVICE container with ServiceType = "Inspection"

Test-code references: None found in top-level Python test files.

### UAD1524 — FirstName

Category: other_conditional_scoped

Rule logic: If FirstName is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1525 — LastName

Category: other_conditional_scoped

Rule logic: If LastName is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1526 — AppraiserLicenseType

Category: other_conditional_scoped

Rule logic: If AppraiserLicenseType is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1528 — LicenseExpirationDate

Category: other_conditional_scoped

Rule logic: If LicenseExpirationDate is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1531 — LicenseIdentifier

Category: other_conditional_scoped

Rule logic: If LicenseIdentifier is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1532 — LicenseIssuingAuthorityStateCode

Category: other_conditional_scoped

Rule logic: If LicenseIssuingAuthorityStateCode is not provided for PartyRoleType = "AppraiserSupervisor"

Test-code references: None found in top-level Python test files.

### UAD1537 — AddressLineText

Category: other_conditional_scoped

Rule logic: If AddressLineText is not provided for PartyRoleType = "Client"

Test-code references: None found in top-level Python test files.

### UAD1538 — CityName

Category: other_conditional_scoped

Rule logic: If CityName is not provided for PartyRoleType = "Client"

Test-code references: None found in top-level Python test files.

### UAD1539 — PostalCode

Category: other_conditional_scoped

Rule logic: If PostalCode is not provided for PartyRoleType = "Client"

Test-code references: None found in top-level Python test files.

### UAD1540 — StateCode

Category: other_conditional_scoped

Rule logic: If StateCode is not provided for PartyRoleType = "Client"

Test-code references: None found in top-level Python test files.

### UAD1541 — FullName

Category: other_conditional_scoped

Rule logic: If FullName is not provided for PartyRoleType = "Client"

Test-code references: None found in top-level Python test files.

### UAD1544 — FirstName

Category: other_conditional_scoped

Rule logic: If FirstName is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1545 — LastName

Category: other_conditional_scoped

Rule logic: If LastName is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1546 — AppraiserLicenseType

Category: other_conditional_scoped

Rule logic: If AppraiserLicenseType is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1548 — LicenseExpirationDate

Category: other_conditional_scoped

Rule logic: If AppraiserLicenseType <> "None" and LicenseExpirationDate is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1551 — LicenseIdentifier

Category: other_conditional_scoped

Rule logic: If AppraiserLicenseType <> "None" and LicenseIdentifier is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1552 — LicenseIssuingAuthorityStateCode

Category: other_conditional_scoped

Rule logic: If AppraiserLicenseType <> "None" and LicenseIssuingAuthorityStateCode is not provided for PartyRoleType = "Appraiser"

Test-code references: None found in top-level Python test files.

### UAD1560 — FullName

Category: other_conditional_scoped

Rule logic: If PartyRoleType = "Lender" or "ManagementCompany" and FullName is not provided

Test-code references: None found in top-level Python test files.

### UAD1580 — CooperativeProprietaryLeaseExpirationDate

Category: other_conditional_scoped

Rule logic: If ProjectLegalStructureType = "Cooperative" or "Condop", and CooperativeProprietaryLeaseExpirationDate is not provided

Test-code references: None found in top-level Python test files.

### UAD1581 — PropertyCooperativeSharesCount

Category: other_conditional_scoped

Rule logic: If ProjectLegalStructureType = "Cooperative" or "Condop", and PropertyCooperativeSharesCount is not provided

Test-code references: None found in top-level Python test files.

### UAD1588 — UPBProRataShareAttributableToUnitAmount

Category: other_conditional_scoped

Rule logic: If ProjectBlanketFinancingIndicator = "true", and LineOfCreditIndicator = "false", and UPBProRataShareAttributableToUnitAmount is not provided in a given instance of PROJECT_BLANKET_FINANCING

Test-code references: None found in top-level Python test files.

### UAD1589 — UPBAmount

Category: other_conditional_scoped

Rule logic: If ProjectBlanketFinancingIndicator = "true", and LineOfCreditIndicator = "false", and UPBAmount is not provided in a given instance of PROJECT_BLANKET_FINANCING

Test-code references: None found in top-level Python test files.

### UAD1591 — ProjectConversionOriginalUseType

Category: other_conditional_scoped

Rule logic: If (PropertyInProjectIndicator = "true" and ProjectConversionIndicator = "true"), and ProjectConversionOriginalUseType is not provided

Test-code references: None found in top-level Python test files.

### UAD1593 — LegalActionIndicator

Category: other_conditional_scoped

Rule logic: If (PropertyInProjectIndicator = "true" or PUDIndicator = "true") and LegalActionIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1595 — ProjectCommercialSpacePercent

Category: other_conditional_scoped

Rule logic: If PropertyInProjectIndicator = "true", and ProjectCommercialSpaceIndicator = "true", and ProjectCommercialSpacePercent is not provided

Test-code references: None found in top-level Python test files.

### UAD1601 — SubjectBuildingCompletedIndicator

Category: other_conditional_scoped

Rule logic: If (PropertyInProjectIndicator = "true" and ProjectCompletedIndicator = "false") and SubjectBuildingCompletedIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1602 — ProjectDeveloperOrSponsorControlsProjectManagementIndicator

Category: other_conditional_scoped

Rule logic: If (PropertyInProjectIndicator = "true" or PUDIndicator = "true") and ProjectDeveloperOrSponsorControlsProjectManagementIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1606 — ProjectBlanketFinancingIndicator

Category: other_conditional_scoped

Rule logic: If ProjectLegalStructureType = "Cooperative" or "Condop", and ProjectBlanketFinancingIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1607 — ProjectTotalSharesIssuedAndOutstandingCount

Category: other_conditional_scoped

Rule logic: If ProjectLegalStructureType = "Cooperative" or "Condop", and ProjectTotalSharesIssuedAndOutstandingCount is not provided

Test-code references: None found in top-level Python test files.

### UAD1608 — SingleEntityGreatestNumberOfSharesCount

Category: other_conditional_scoped

Rule logic: If ProjectLegalStructureType = "Cooperative" or "Condop", and SingleEntityGreatestNumberOfSharesCount is not provided

Test-code references: None found in top-level Python test files.

### UAD1610 — PropertyTaxAbatementsOrExemptionsIndicator

Category: other_conditional_scoped

Rule logic: If (PropertyInProjectIndicator = "true" or PUDIndicator = "true") and PropertyTaxAbatementsOrExemptionsIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1656 — ImageCategoryType

Category: alternative_mutually_exclusive

Rule logic: If PriceTrendsAnalysisDescription is not provided, and ImageCategoryType = "PriceTrendGraph" is not provided in any instance of IMAGE

Test-code references: None found in top-level Python test files.

### UAD1657 — DataSourceName

Category: other_conditional_scoped

Rule logic: If DataSourceName is not provided in a given instance of DATA_SOURCE that captures the Price Trend Source

Test-code references: None found in top-level Python test files.

### UAD1675 — VehicleStorageDefectsExistIndicator

Category: other_conditional_scoped

Rule logic: If CarStorageType <> "None" and VehicleStorageDefectsExistIndicator is not provided

Test-code references: None found in top-level Python test files.

### UAD1688 — UnitInteriorDefectsExistIndicator

Category: other_conditional_scoped

Rule logic: If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitInteriorDefectsExistIndicator is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1695 — EffectiveAgeYearsCount

Category: alternative_mutually_exclusive

Rule logic: If CostApproachIndicator = "true" and ImprovementType = "Dwelling" and EffectiveAgeYearsCount is provided, and (either or both of EffectiveAgeRangeLowYearsCount or EffectiveAgeRangeHighYearsCount is provided) in a given instance of STRUCTURE_ANALYSIS_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1696 — EffectiveAgeYearsCount

Category: alternative_mutually_exclusive

Rule logic: If CostApproachIndicator = "true" and ImprovementType = "Dwelling" and EffectiveAgeYearsCount is not provided, and (either EffectiveAgeRangeLowYearsCount or EffectiveAgeRangeHighYearsCount is not provided) in a given instance of STRUCTURE_ANALYSIS_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1698 — OwnershipTransferTransactionAmount

Category: alternative_mutually_exclusive

Rule logic: If PriorSalesOrTransfersIndicator = "true" and ((OwnershipTransferTransactionAmount and OwnershipTransferAmountNotAvailableReasonType are not provided) or (OwnershipTransferTransactionAmount and OwnershipTransferAmountNotAvailableReasonType are provided))

Test-code references: None found in top-level Python test files.

### UAD1699 — LastName

Category: alternative_mutually_exclusive

Rule logic: If neither FullName nor LastName is provided for PartyRoleType = "PropertySeller"

Test-code references: None found in top-level Python test files.

### UAD1700 — LastName

Category: alternative_mutually_exclusive

Rule logic: If neither FullName nor LastName is provided for PartyRoleType = "PropertyOwner"

Test-code references: None found in top-level Python test files.

### UAD1701 — LastName

Category: alternative_mutually_exclusive

Rule logic: If neither FullName nor LastName is provided for PartyRoleType = "Borrower"

Test-code references: None found in top-level Python test files.

### UAD1715 — DefectComponentLabelType

Category: other_conditional_scoped

Rule logic: If DefectComponentLabelType is not provided in a given instance of DEFECT_DETAIL that is not associated with AMENTIY or CAR_STORAGE

Test-code references: None found in top-level Python test files.

### UAD1720 — DepreciationTotalAmount

Category: alternative_mutually_exclusive

Rule logic: If CostApproachIndicator = "true" and DepreciationTotalAmount is not provided, and (DepreciationExternalAmount or DepreciationFunctionalAmount or DepreciationPhysicalAmount are not provided) in a given instance of IMPROVEMENT_COST_AND_DEPRECIATED_VALUE/IMPROVEMENT_DEPRECIATION

Test-code references: None found in top-level Python test files.

### UAD1731 — SalesContractDate

Category: other_conditional_scoped

Rule logic: IF @ValuationUseType = "SalesComparable" AND ContractDateUnknownIndicator = "false", and SalesContractDate is not provided

Test-code references: None found in top-level Python test files.

### UAD1733 — MarketingOrExposureDaysCount

Category: alternative_mutually_exclusive

Rule logic: If MarketingOrExposureDaysCount is provided, and (either or both of MarketingOrExposureLowRangeDaysCount or MarketingOrExposureHighRangeDaysCount is provided)

Test-code references: None found in top-level Python test files.

### UAD1746 — MarketingOrExposureDaysCount

Category: alternative_mutually_exclusive

Rule logic: If MarketingOrExposureDaysCount is not provided, and (either MarketingOrExposureLowRangeDaysCount or MarketingOrExposureHighRangeDaysCount is not provided)

Test-code references: None found in top-level Python test files.

### UAD1771 — SaleType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and OwnershipTransferTransactionType = "Sale" and SaleType is not provided in a given instance of SALES_HISTORY

Test-code references: None found in top-level Python test files.

### UAD1772 — FloorIdentifier

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and  ImprovementType = "Dwelling" and AttachmentType = "Attached" and StructuralDesignType = ("Lowrise" or "Highrise" or "Midrise"), and FloorIdentifier is not provided in a given instance of PROPERTY_UNIT_DETAIL

Test-code references: None found in top-level Python test files.

### UAD1773 — PropertyEstateType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (PropertyInProjectIndicator = "false" or (PropertyInProjectIndicator = "true" and ProjectLegalStructureType = "Condominium")), and PropertyEstateType is not provided

Test-code references: None found in top-level Python test files.

### UAD1775 — ManufacturedHomeWidthType

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured" and ManufacturedHomeWidthType is not provided

Test-code references: None found in top-level Python test files.

### UAD1776 — UnitBelowGradeUnfinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and UnitBelowGradeUnfinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA

Test-code references: None found in top-level Python test files.

### UAD1777 — UnitNonStandardBelowGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and  OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitNonStandardBelowGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitNonStandardBelowGradeFinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit)

Test-code references: None found in top-level Python test files.

### UAD1778 — UnitAboveGradeUnfinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and  OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitAboveGradeUnfinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitAboveGradeUnfinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit)

Test-code references: None found in top-level Python test files.

### UAD1779 — UnitNonStandardAboveGradeFinishedAreaMeasure

Category: other_conditional_scoped

Rule logic: If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitNonStandardAboveGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitNonStandardAboveGradeFinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit)

Test-code references: None found in top-level Python test files.
