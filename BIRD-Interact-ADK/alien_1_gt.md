# BIRD-Interact Ground Truth — `alien_1`

## Overview

| Field | Value |
|---|---|
| `instance_id` | alien_1 |
| `selected_database` | alien |
| `category` | Query |
| `difficulty_tier` | Moderate |
| `high_level` | True |

## User queries

### Ambiguous benchmark query

I want to analyze how the signal quality varies across different atmospheric conditions. For each condition, give condition name, the average quality value, the median quality value, and count how many usable signals there are. Sort the result by average value.

### Unmasked / reference query

I want to analyze how the Signal-to-Noise Quality Indicator (SNQI) varies across different weather conditions. For each weather condition, give weather condition name, the average SNQI, the median SNQI, and count how many analyzable signals there are. Sort the result by average SNQI in descending order.

## Critical user-query ambiguities

| Term | Type | Masked? | SQL snippet | Extra |
|---|---|---:|---|---|
| signal quality | `knowledge_linking_ambiguity` | `True` | `s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI` |  |
| good signals | `knowledge_linking_ambiguity` | `True` | `COUNT(*) FILTER (WHERE SNQI > 0) as analyzable signals` |  |

## Non-critical user-query ambiguities

| Term | Type | Masked? | SQL snippet | Extra |
|---|---|---:|---|---|
| order | `sort_ambiguity` | `False` | `ORDER BY avg_snqi DESC` |  |

## Knowledge ambiguities

| Term | Type | Masked? | SQL snippet | Extra |
|---|---|---:|---|---|
| Signal-to-Noise Quality Indicator (SNQI) | `knowledge_ambiguity` | `False` | `s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI` | {"deleted_knowledge": 0} |

## External knowledge IDs

```json
[
  0,
  50
]
```

## Ground-truth SQL

### SQL 1

```sql
/* 
Intent: Analyze signal quality (SNQI) with atmospheric conditions using window functions
Knowledge Used: SNQI (id:0)
Advanced Features: Window functions, conditional aggregation
*/
WITH signal_quality AS (
    -- Step 1: Calculate SNQI for all signals with their observation conditions
    SELECT 
        s.SignalRegistry,
        s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI,
        o.WeathProfile
    FROM Signals s
    JOIN Telescopes t ON s.TelescRef = t.TelescRegistry
    JOIN Observatories o ON t.ObservStation = o.ObservStation
)
-- Step 2: Rank signals by quality within weather profiles
SELECT 
    WeathProfile,
    AVG(SNQI) AS avg_snqi,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY SNQI) AS median_snqi,
    COUNT(*) FILTER (WHERE SNQI > 0) AS analyzable_signals
FROM signal_quality
GROUP BY WeathProfile
ORDER BY avg_snqi DESC;
```

## Preprocess SQL

*None.*

## Cleanup SQL

*None.*

## Evaluation conditions

```json
{
  "decimal": -1,
  "distinct": false,
  "order": true
}
```

## Test cases

```json
[]
```

## Follow-up

### Query

How does the Atmospheric Observability Index (AOI) vary across different weather conditions? For each weather condition, provide: Weather condition name, Average AOI, Median AOI, Count of valid observations (AOI > 0), Sorted by average AOI in descending order.

- **type:** `attribute_change`
- **category:** `Query`
- **difficulty_tier:** `Moderate`

### Follow-up ground-truth SQL

```sql
/*
Intent: Analyze Atmospheric Observability Index (AOI) with weather conditions
Knowledge Used: AOI (id:1)
Advanced Features: Window functions, conditional aggregation
*/

WITH observ_conditions AS (
    -- Step 1: Calculate AOI for all signals with their observation conditions
    SELECT 
        s.SignalRegistry,
        o.AtmosTransparency * (1 - o.HumidityRate / 100) * (1 - 0.02 * o.WindSpeedMs) AS AOI,
        o.WeathProfile
    FROM 
        Signals s
    JOIN 
        Telescopes t ON s.TelescRef = t.TelescRegistry
    JOIN 
        Observatories o ON t.ObservStation = o.ObservStation
)

-- Step 2: Aggregate AOI metrics by weather profile
SELECT 
    WeathProfile,
    AVG(AOI) AS avg_aoi,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY AOI) AS median_aoi,
    COUNT(*) FILTER (WHERE AOI > 0) AS valid_observations
FROM 
    observ_conditions
GROUP BY 
    WeathProfile
ORDER BY 
    avg_aoi DESC;
```

### `external_knowledge`

```json
[
  1
]
```

### `conditions`

```json
{
  "decimal": -1,
  "distinct": false,
  "order": true
}
```

### `test_cases`

```json
[]
```

## Appendix — full raw record

<details><summary>Expand full JSON (no fields omitted)</summary>

```json
{
  "instance_id": "alien_1",
  "selected_database": "alien",
  "query": "I want to analyze how the Signal-to-Noise Quality Indicator (SNQI) varies across different weather conditions. For each weather condition, give weather condition name, the average SNQI, the median SNQI, and count how many analyzable signals there are. Sort the result by average SNQI in descending order.",
  "preprocess_sql": [],
  "clean_up_sqls": [],
  "sol_sql": [
    "/* \nIntent: Analyze signal quality (SNQI) with atmospheric conditions using window functions\nKnowledge Used: SNQI (id:0)\nAdvanced Features: Window functions, conditional aggregation\n*/\nWITH signal_quality AS (\n    -- Step 1: Calculate SNQI for all signals with their observation conditions\n    SELECT \n        s.SignalRegistry,\n        s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI,\n        o.WeathProfile\n    FROM Signals s\n    JOIN Telescopes t ON s.TelescRef = t.TelescRegistry\n    JOIN Observatories o ON t.ObservStation = o.ObservStation\n)\n-- Step 2: Rank signals by quality within weather profiles\nSELECT \n    WeathProfile,\n    AVG(SNQI) AS avg_snqi,\n    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY SNQI) AS median_snqi,\n    COUNT(*) FILTER (WHERE SNQI > 0) AS analyzable_signals\nFROM signal_quality\nGROUP BY WeathProfile\nORDER BY avg_snqi DESC;"
  ],
  "external_knowledge": [
    0,
    50
  ],
  "test_cases": [],
  "category": "Query",
  "high_level": true,
  "conditions": {
    "decimal": -1,
    "distinct": false,
    "order": true
  },
  "amb_user_query": "I want to analyze how the signal quality varies across different atmospheric conditions. For each condition, give condition name, the average quality value, the median quality value, and count how many usable signals there are. Sort the result by average value.",
  "user_query_ambiguity": {
    "critical_ambiguity": [
      {
        "term": "signal quality",
        "sql_snippet": "s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI",
        "is_mask": true,
        "type": "knowledge_linking_ambiguity"
      },
      {
        "term": "good signals",
        "sql_snippet": "COUNT(*) FILTER (WHERE SNQI > 0) as analyzable signals",
        "is_mask": true,
        "type": "knowledge_linking_ambiguity"
      }
    ],
    "non_critical_ambiguity": [
      {
        "term": "order",
        "sql_snippet": "ORDER BY avg_snqi DESC",
        "is_mask": false,
        "type": "sort_ambiguity"
      }
    ]
  },
  "knowledge_ambiguity": [
    {
      "term": "Signal-to-Noise Quality Indicator (SNQI)",
      "sql_snippet": "s.SnrRatio - 0.1 * ABS(s.NoiseFloorDbm) AS SNQI",
      "is_mask": false,
      "type": "knowledge_ambiguity",
      "deleted_knowledge": 0
    }
  ],
  "follow_up": {
    "query": "How does the Atmospheric Observability Index (AOI) vary across different weather conditions? For each weather condition, provide: Weather condition name, Average AOI, Median AOI, Count of valid observations (AOI > 0), Sorted by average AOI in descending order.",
    "sol_sql": "/*\nIntent: Analyze Atmospheric Observability Index (AOI) with weather conditions\nKnowledge Used: AOI (id:1)\nAdvanced Features: Window functions, conditional aggregation\n*/\n\nWITH observ_conditions AS (\n    -- Step 1: Calculate AOI for all signals with their observation conditions\n    SELECT \n        s.SignalRegistry,\n        o.AtmosTransparency * (1 - o.HumidityRate / 100) * (1 - 0.02 * o.WindSpeedMs) AS AOI,\n        o.WeathProfile\n    FROM \n        Signals s\n    JOIN \n        Telescopes t ON s.TelescRef = t.TelescRegistry\n    JOIN \n        Observatories o ON t.ObservStation = o.ObservStation\n)\n\n-- Step 2: Aggregate AOI metrics by weather profile\nSELECT \n    WeathProfile,\n    AVG(AOI) AS avg_aoi,\n    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY AOI) AS median_aoi,\n    COUNT(*) FILTER (WHERE AOI > 0) AS valid_observations\nFROM \n    observ_conditions\nGROUP BY \n    WeathProfile\nORDER BY \n    avg_aoi DESC;",
    "external_knowledge": [
      1
    ],
    "type": "attribute_change",
    "test_cases": [],
    "category": "Query",
    "difficulty_tier": "Moderate",
    "conditions": {
      "decimal": -1,
      "distinct": false,
      "order": true
    }
  },
  "difficulty_tier": "Moderate"
}
```

</details>
