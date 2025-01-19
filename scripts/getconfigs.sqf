// File Format Description:
// -----------------------
// Database: ConfigExtract_YYYY-MM-DD_HH-MM-SS.ini
//
// Sections:
// 1. Validation
//    - Keys: TotalClasses, Categories, Stats_CategoryName
// 2. CategoryData_[CategoryName]
//    - Keys: CSV lines with format ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model
//
// Note: Ensure INIDBI2 is configured and available before running this script.

// Debug flag to control category scope
private _debugMode = false;  // Set to true for limited testing categories

private ["_classHierarchy", "_configs"];

// Define categories based on debug mode
private _categories = if (_debugMode) then {
    // Limited set for testing/debugging
    ["CfgWeapons", "CfgVehicles"]
} else {
    // Scan for all available categories in configFile
    private _allCategories = [];
    for "_i" from 0 to (count configFile - 1) do {
        private _entry = configFile select _i;
        if (isClass _entry) then {
            _allCategories pushBack (configName _entry);
        };
    };
    _allCategories
};

diag_log text format ["Running in %1 mode with %2 categories", ["FULL", "DEBUG"] select _debugMode, count _categories];

diag_log text format ["Starting config extraction..."];

// Initialize database early
private _timestamp = systemTime apply { if (_x < 10) then { "0" + str _x } else { str _x } };
private _dbName = format ["ConfigExtract_%1-%2-%3_%4-%5-%6", 
    _timestamp#0, _timestamp#1, _timestamp#2,
    _timestamp#3, _timestamp#4, _timestamp#5
];
private _db = ["new", _dbName] call OO_INIDBI;

// Track statistics and results
private _totalClasses = 0;
private _categoryStats = createHashMap;
private _categoryData = createHashMap;

// Optimized config processor
private _processConfig = {
    params ["_config", "_category"];
    private _stack = [[_config, ""]];
    private _processed = 0;
    private _results = [];
    
    while {count _stack > 0} do {
        _processed = _processed + 1;
        if (_processed mod 10000 == 0) then {
            diag_log text format ["Processed %1 entries in %2...", _processed, _category];
        };
        
        private _current = _stack deleteAt 0;
        _current params ["_entry", "_currentParent"];
        
        private _entryName = configName _entry;
        for "_i" from 0 to (count _entry - 1) do {
            private _subEntry = _entry select _i;
            if (isClass _subEntry) then {
                private _className = configName _subEntry;
                if (_className != "") then {
                    private _sourceList = configSourceModList _subEntry;
                    private _source = if (count _sourceList > 0) then { _sourceList select 0 } else { "A3" };
                    
                    private _inheritedClass = inheritsFrom _subEntry;
                    private _inheritsFrom = if (isNull _inheritedClass) then { "" } else { configName _inheritedClass };
                    
                    // Extract additional class information
                    private _isSimpleObject = getNumber (_subEntry >> "canBeSimpleObject") > 0;
                    private _numProperties = count (_subEntry);
                    private _scope = getNumber (_subEntry >> "scope");
                    private _model = getText (_subEntry >> "model");
                    
                    _results pushBack ([
                        _className, _source, _category, _entryName, _inheritsFrom,
                        str _isSimpleObject, str _numProperties, str _scope, _model
                    ] joinString ",");
                    
                    _totalClasses = _totalClasses + 1;
                    _categoryStats set [_category, (_categoryStats getOrDefault [_category, 0]) + 1];
                    
                    _stack pushBack [_subEntry, _className];
                };
            };
        };
    };
    _results
};

// Process categories
{
    private _category = _x;
    private _sectionName = format ["CategoryData_%1", _category];
    
    diag_log text format ["Processing %1...", _category];
    private _results = [(configFile >> _category), _category] call _processConfig;
    
    // Write entire category at once
    ["write", [_sectionName, "header", "ClassName,Source,Category,Parent,InheritsFrom,IsSimpleObject,NumProperties,Scope,Model"]] call _db;
    {
        ["write", [_sectionName, str _forEachIndex, _x]] call _db;
    } forEach _results;
    
    diag_log text format ["Wrote %1 with %2 classes", _category, count _results];
} forEach _categories;

// Write validation info at the end
["write", ["Validation", "TotalClasses", _totalClasses]] call _db;
["write", ["Validation", "Categories", _categories]] call _db;

{
    private _statsKey = format ["Stats_%1", _x];
    ["write", ["Validation", _statsKey, _categoryStats get _x]] call _db;
} forEach _categories;

// Clean up
["delete", _db] call OO_INIDBI;

diag_log text format ["Completed config extraction to %1", _dbName];