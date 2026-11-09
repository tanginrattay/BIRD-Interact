# mental_9

[Task index](README.md)

## task_id

```text
mental_9
```

## instance_id

```text
mental_9
```

## database

```text
mental
```

## phase1_passed

```json
true
```

## phase2_passed

```json
false
```

## has_follow_up

```json
true
```

## total_reward

```json
0.7
```

## elapsed_seconds

```json
53.06170654296875
```

## budget_used

```json
17.0
```

## budget_remaining

```json
1.0
```

## dialogue_history

```json
[
  {
    "role": "agent",
    "content": "Does “prevalence over 20%” mean Suicide Risk Prevalence (assessments with High or Severe suicide risk), or the broader High-Risk Patient definition that also includes PHQ-9 or GAD-7 scores over 15?"
  },
  {
    "role": "user",
    "content": "“Prevalence over 20%” refers specifically to Suicide Risk Prevalence — the percentage of assessments with High or Severe suicide risk. It does not include the broader high-risk patient definition based on PHQ-9 or GAD-7 scores over 15."
  },
  {
    "role": "agent",
    "content": "What formula should I use for Resource-Demand Differential (RDD)? It is referenced in the available definitions, but its formula is not provided."
  },
  {
    "role": "user",
    "content": "The Resource-Demand Differential (RDD) is calculated as the difference between the Patient Functional Impairment Score (PFIS) and the Facility Resource Adequacy Index (FRAI): RDD = PFIS − FRAI. A higher RDD indicates a greater gap between patient needs and available facility resources."
  },
  {
    "role": "agent",
    "content": "How many top facilities should I list, ranked by highest RDD?"
  },
  {
    "role": "user",
    "content": "The task specifies listing the top 100 facilities ranked by highest RDD (Resource-Demand Differential). So you should show up to 100 facilities, ordered by RDD from highest to lowest."
  }
]
```

## tool_trajectory

```json
[
  {
    "type": "tool",
    "tool": "get_schema",
    "args": {},
    "result": "CREATE TABLE \"facilities\" (\nfackey character varying NOT NULL,\nrsource USER-DEFINED NULL,\nenvstress USER-DEFINED NULL,\nlifeimpact USER-DEFINED NULL,\nseasonpat USER-DEFINED NULL,\nleglissue USER-DEFINED NULL,\nssystemchg USER-DEFINED NULL,\nsupport_and_resources jsonb NULL,\n    PRIMARY KEY (fackey)\n);\n\nFirst 3 rows:\nfackey    rsource    envstress    lifeimpact    seasonpat    leglissue    ssystemchg    support_and_resources\n--------  ---------  -----------  ------------  -----------  -----------  ------------  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\nF306      Emergency  Severe       Mild          Winter       Ongoing      Variable      {'plans': {'crisis_plan_status': 'Needs Update', 'safety_plan_status': 'Not Needed'}, 'support_services': 'Housing,Employment,Case Management', 'emergency_contact': '3', 'community_resources': 'Limited'}\nF492      Court      Mild         Mild          Winter       Resolved     Variable      {'plans': {'crisis_plan_status': 'Not Needed', 'safety_plan_status': 'Needs Update'}, 'support_services': '', 'emergency_contact': '1', 'community_resources': 'Limited'}\nF562      Emergency  Moderate     Severe        Variable     Resolved     Improved      {'plans': {'crisis_plan_status': 'In Place', 'safety_plan_status': 'In Place'}, 'support_services': 'Case Management,Employment,None', 'emergency_contact': '1', 'community_resources': 'Adequate'}\n...\n\n\nCREATE TABLE \"treatmentbasics\" (\ntxkey integer NOT NULL DEFAULT nextval('treatmentbasics_txkey_seq'::regclass),\nencref character varying NOT NULL,\ncurmed text NULL,\nmedadh USER-DEFINED NULL,\nmedside USER-DEFINED NULL,\nmedchg USER-DEFINED NULL,\ncrisisint numeric NULL,\ntherapy_details jsonb NULL,\n    PRIMARY KEY (txkey),\n    FOREIGN KEY (encref) REFERENCES encounters(enckey)\n);\n\nFirst 3 rows:\n  txkey  encref    curmed                         ...<truncated>",
    "cost": 1.0,
    "budget_before": 18.0,
    "budget_after": 17.0
  },
  {
    "type": "tool",
    "tool": "get_all_knowledge_definitions",
    "args": {},
    "result": "[\n  {\n    \"id\": 0,\n    \"knowledge\": \"Average PHQ-9 Score by Facility (APSF)\",\n    \"description\": \"Calculates the average PHQ-9 depression score for patients assessed at a specific facility.\",\n    \"definition\": \"APSF = \\\\frac{\\\\sum_{i \\\\in assessmentsymptomsandrisk} (mental\\\\_health\\\\_scores_i['depression']['phq9\\\\_score'])} {|assessmentsymptomsandrisk|}\"\n  },\n  {\n    \"id\": 1,\n    \"knowledge\": \"Average GAD-7 Score by Facility (AGSF)\",\n    \"description\": \"Calculates the average GAD-7 anxiety score for patients assessed at a specific facility.\",\n    \"definition\": \"AGSF = \\\\frac{\\\\sum_{i \\\\in assessmentsymptomsandrisk} (mental\\\\_health\\\\_scores_i['anxiety']['gad7\\\\_score'])} {|assessmentsymptomsandrisk|}, \\\\text{where } mental\\\\_health\\\\_scores_i['anxiety']['gad7\\\\_score'] \\\\text{ is the GAD-7 score for each assessment in the assessmentsymptomsandrisk table, linked to a facility via encounters.facid}\"\n  },\n  {\n    \"id\": 2,\n    \"knowledge\": \"Treatment Adherence Rate (TAR)\",\n    \"description\": \"Measures the proportion of patients with high or medium treatment adherence at a facility.\",\n    \"definition\": \"TAR = \\\\frac{|treatmentoutcomes \\\\text{ with } txadh \\\\in \\\\{High, Medium\\\\}|} {|treatmentoutcomes|}\"\n  },\n  {\n    \"id\": 3,\n    \"knowledge\": \"Suicide Risk Prevalence (SRP)\",\n    \"description\": \"Calculates the percentage of assessments indicating high or severe suicide risk at a facility.\",\n    \"definition\": \"SRP = \\\\frac{|assessmentsymptomsandrisk \\\\text{ with } suicrisk \\\\in \\\\{High, Severe\\\\}|} {|assessmentsymptomsandrisk|} \\\\times 100\"\n  },\n  {\n    \"id\": 4,\n    \"knowledge\": \"Therapy Engagement Score (TES)\",\n    \"description\": \"Computes an average engagement score across therapy sessions.\",\n    \"definition\": \"TES = \\\\frac{\\\\sum_{i \\\\in treatmentbasics} (therapy\\\\_details_i['engagement\\\\_score'])} {|treatmentbasics|}, \\\\text{where } engagement\\\\_score = \\\\begin{cases} 3 & \\\\text{if } therapy\\\\_details['engagement'] = High \\\\\\\\ 2 & \\\\text{if } therapy\\\\_details['engagemen...<truncated>",
    "cost": 1.0,
    "budget_before": 17.0,
    "budget_after": 16.0
  },
  {
    "type": "tool",
    "tool": "ask_user",
    "args": {
      "question": "Does “prevalence over 20%” mean Suicide Risk Prevalence (assessments with High or Severe suicide risk), or the broader High-Risk Patient definition that also includes PHQ-9 or GAD-7 scores over 15?"
    },
    "result": "“Prevalence over 20%” refers specifically to Suicide Risk Prevalence — the percentage of assessments with High or Severe suicide risk. It does not include the broader high-risk patient definition based on PHQ-9 or GAD-7 scores over 15.",
    "cost": 2.0,
    "budget_before": 16.0,
    "budget_after": 14.0
  },
  {
    "type": "tool",
    "tool": "ask_user",
    "args": {
      "question": "What formula should I use for Resource-Demand Differential (RDD)? It is referenced in the available definitions, but its formula is not provided."
    },
    "result": "The Resource-Demand Differential (RDD) is calculated as the difference between the Patient Functional Impairment Score (PFIS) and the Facility Resource Adequacy Index (FRAI): RDD = PFIS − FRAI. A higher RDD indicates a greater gap between patient needs and available facility resources.",
    "cost": 2.0,
    "budget_before": 14.0,
    "budget_after": 12.0
  },
  {
    "type": "tool",
    "tool": "ask_user",
    "args": {
      "question": "How many top facilities should I list, ranked by highest RDD?"
    },
    "result": "The task specifies listing the top 100 facilities ranked by highest RDD (Resource-Demand Differential). So you should show up to 100 facilities, ordered by RDD from highest to lowest.",
    "cost": 2.0,
    "budget_before": 12.0,
    "budget_after": 10.0
  },
  {
    "type": "tool",
    "tool": "execute_sql",
    "args": {
      "sql": "WITH risk AS (\n    SELECT e.facid,\n           100.0 * COUNT(*) FILTER (WHERE r.suicrisk IN ('High', 'Severe')) / COUNT(*) AS srp\n    FROM encounters e\n    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\n    GROUP BY e.facid\n), impairment AS (\n    SELECT e.facid,\n           AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 END) AS pfis\n    FROM encounters e\n    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\n    GROUP BY e.facid\n), scores AS (\n    SELECT f.fackey AS facility_id, i.pfis,\n           CASE f.support_and_resources ->> 'community_resources'\n               WHEN 'Comprehensive' THEN 3\n               WHEN 'Adequate' THEN 2\n               WHEN 'Limited' THEN 1\n           END AS frai\n    FROM facilities f\n    JOIN risk r ON r.facid = f.fackey\n    JOIN impairment i ON i.facid = f.fackey\n    WHERE r.srp > 20\n)\nSELECT facility_id, pfis, frai, pfis - frai AS rdd\nFROM scores\nORDER BY rdd DESC, facility_id\nLIMIT 100;"
    },
    "result": "facility_id | pfis | frai | rdd ------------------------------- F105 | 3.0000000000000000 | 1 | 2.0000000000000000 F123 | 3.0000000000000000 | 1 | 2.0000000000000000 F131 | 3.0000000000000000 | 1 | 2.0000000000000000 F152 | 3.0000000000000000 | 1 | 2.0000000000000000 F167 | 3.0000000000000000 | 1 | 2.0000000000000000 F184 | 3.0000000000000000 | 1 | 2.0000000000000000 F218 | 3.0000000000000000 | 1 | 2.0000000000000000 F228 | 3.0000000000000000 | 1 | 2.0000000000000000 F247 | 3.0000000000000000 | 1 | 2.0000000000000000 F248 | 3.0000000000000000 | 1 | 2.0000000000000000 F282 | 3.0000000000000000 | 1 | 2.0000000000000000 F289 | 3.0000000000000000 | 1 | 2.0000000000000000 F324 | 3.0000000000000000 | 1 | 2.0000000000000000 F351 | 3.0000000000000000 | 1 | 2.0000000000000000 F383 | 3.0000000000000000 | 1 | 2.0000000000000000 F452 | 3.0000000000000000 | 1 | 2.0000000000000000 F460 | 3.0000000000000000 | 1 | 2.0000000000000000 F559 | 3.0000000000000000 | 1 | 2.0000000000000000 F703 | 3.0000000000000000 | 1 | 2.0000000000000000 F719 | 3.0000000000000000 | 1 | 2.0000000000000000 F743 | 3.0000000000000000 | 1 | 2.0000000000000000 F755 | 3.0000000000000000 | 1 | 2.0000000000000000 F906 | 3.0000000000000000 | 1 | 2.0000000000000000 F915 | 3.0000000000000000 | 1 | 2.0000000000000000 F919 | 3.0000000000000000 | 1 | 2.0000000000000000 F944 | 3.0000000000000000 | 1 | 2.0000000000000000 F990 | 3.0000000000000000 | 1 | 2.0000000000000000 F991 | 3.0000000000000000 | 1 | 2.0000000000000000 F156 | 2.6666666666666667 | 1 | 1.6666666666666667 F163 | 2.5000000000000000 | 1 | 1.5000000000000000 F309 | 2.5000000000000000 | 1 | 1.5000000000000000 F335 | 2.5000000000000000 | 1 | 1.5000000000000000 F393 | 2.5000000000000000 | 1 | 1.5000000000000000 F439 | 2.5000000000000000 | 1 | 1.5000000000000000 F450 | 2.5000000000000000 | 1 | 1.5000000000000000 F650 | 2.5000000000000000 | 1 | 1.5000000000000000 F941 | 2.5000000000000000 | 1 | 1.5000000000000000 F284 | 2.3333333333333333 | 1 | 1.333333333333333...<truncated>",
    "cost": 1.0,
    "budget_before": 10.0,
    "budget_after": 9.0
  },
  {
    "type": "tool",
    "tool": "submit_sql",
    "args": {
      "sql": "WITH risk AS (\n    SELECT e.facid,\n           100.0 * COUNT(*) FILTER (WHERE r.suicrisk IN ('High', 'Severe')) / COUNT(*) AS srp\n    FROM encounters e\n    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\n    GROUP BY e.facid\n), impairment AS (\n    SELECT e.facid,\n           AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 END) AS pfis\n    FROM encounters e\n    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\n    GROUP BY e.facid\n), scores AS (\n    SELECT f.fackey AS facility_id, i.pfis,\n           CASE f.support_and_resources ->> 'community_resources'\n               WHEN 'Comprehensive' THEN 3\n               WHEN 'Adequate' THEN 2\n               WHEN 'Limited' THEN 1\n           END AS frai\n    FROM facilities f\n    JOIN risk r ON r.facid = f.fackey\n    JOIN impairment i ON i.facid = f.fackey\n    WHERE r.srp > 20\n)\nSELECT facility_id, pfis, frai, pfis - frai AS rdd\nFROM scores\nORDER BY rdd DESC, facility_id\nLIMIT 100;"
    },
    "result": "SQL failed Phase 1. Your SQL is not correct.\nBudget remaining: 6.0 bird-coins",
    "cost": 3.0,
    "budget_before": 9.0,
    "budget_after": 6.0
  },
  {
    "type": "tool",
    "tool": "execute_sql",
    "args": {
      "sql": "SELECT funcimp::text, COUNT(*) FROM assessmentsocialanddiagnosis GROUP BY funcimp; SELECT COUNT(*) AS encounters, COUNT(DISTINCT abref) AS assessments FROM encounters; SELECT COUNT(*) FROM encounters e JOIN assessmentsymptomsandrisk r ON r.asrkey=e.abref LEFT JOIN assessmentsocialanddiagnosis d ON d.asdkey=e.abref WHERE d.asdkey IS NULL;"
    },
    "result": "count\n-----\n0",
    "cost": 1.0,
    "budget_before": 6.0,
    "budget_after": 5.0
  },
  {
    "type": "tool",
    "tool": "execute_sql",
    "args": {
      "sql": "SELECT 'funcimp' AS kind, funcimp::text AS value, COUNT(*) AS n FROM assessmentsocialanddiagnosis GROUP BY funcimp UNION ALL SELECT 'resources', support_and_resources->>'community_resources', COUNT(*) FROM facilities GROUP BY support_and_resources->>'community_resources' UNION ALL SELECT 'encounters', 'distinct assessments', COUNT(DISTINCT abref) FROM encounters UNION ALL SELECT 'encounters', 'total', COUNT(*) FROM encounters;"
    },
    "result": "kind | value | n\n----------------\nfuncimp | Moderate | 252\nfuncimp | Severe | 252\nfuncimp | Mild | 495\nresources | Comprehensive | 159\nresources | Limited | 308\nresources | Adequate | 128\nencounters | distinct assessments | 998\nencounters | total | 999",
    "cost": 1.0,
    "budget_before": 5.0,
    "budget_after": 4.0
  },
  {
    "type": "tool",
    "tool": "submit_sql",
    "args": {
      "sql": "SELECT f.fackey,\n       AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 ELSE 0 END) AS pfis,\n       AVG(CASE f.support_and_resources ->> 'community_resources' WHEN 'Comprehensive' THEN 3 WHEN 'Adequate' THEN 2 WHEN 'Limited' THEN 1 ELSE 0 END) AS frai,\n       AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 ELSE 0 END)\n       - AVG(CASE f.support_and_resources ->> 'community_resources' WHEN 'Comprehensive' THEN 3 WHEN 'Adequate' THEN 2 WHEN 'Limited' THEN 1 ELSE 0 END) AS rdd\nFROM facilities f\nJOIN encounters e ON e.facid = f.fackey\nJOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\nJOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\nGROUP BY f.fackey\nHAVING 100.0 * SUM(CASE WHEN r.suicrisk IN ('High', 'Severe') THEN 1 ELSE 0 END) / COUNT(*) > 20\nORDER BY rdd DESC\nLIMIT 100;"
    },
    "result": "Phase 1 correct! (Reward: 0.7). Moving to Phase 2.\nReward: 0.7\nFollow-up question: Also show Facility Risk Profile Index in the end.\nBudget remaining: 1.0 bird-coins",
    "cost": 3.0,
    "budget_before": 4.0,
    "budget_after": 1.0
  }
]
```

## adk_events

````json
[
  {
    "type": "user_message",
    "message": "Database: mental\nTask ID: mental_9\n\nUser Query:\nFor facilities with lots of high-risk cases wiht prevalence over 20%, calculate the Resource-Demand Differential. List the facility ID, PFIS, FRAI, and RDD scores, showing the top facilities.\n\nYou have a budget of 18.0 bird-coins. Use your tools to explore the database, clarify ambiguities with the user, and submit your final SQL efficiently."
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "get_schema",
          "id": "call_KaibHSHb316JvG16XnW4ssxJ",
          "args": {}
        },
        {
          "type": "function_call",
          "name": "get_all_knowledge_definitions",
          "id": "call_H6plkGpn920sLVS40pCKL2kv",
          "args": {}
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "get_schema",
          "id": "call_KaibHSHb316JvG16XnW4ssxJ",
          "response": "{\"result\": \"CREATE TABLE \\\"facilities\\\" (\\nfackey character varying NOT NULL,\\nrsource USER-DEFINED NULL,\\nenvstress USER-DEFINED NULL,\\nlifeimpact USER-DEFINED NULL,\\nseasonpat USER-DEFINED NULL,\\nleglissue USER-DEFINED NULL,\\nssystemchg USER-DEFINED NULL,\\nsupport_and_resources jsonb NULL,\\n    PRIMARY KEY (fackey)\\n);\\n\\nFirst 3 rows:\\nfackey    rsource    envstress    lifeimpact    seasonpat    leglissue    ssystemchg    support_and_resources\\n--------  ---------  -----------  ------------  -----------  -----------  ------------  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------\\nF306      Emergency  Severe       Mild          Winter       Ongoing      Variable      {'plans': {'crisis_plan_status': 'Needs Update', 'safety_plan_status': 'Not Needed'}, 'support_services': 'Housing,Employment,Case Management', 'emergency_contact': '3', 'community_resources': 'Limited'}\\nF492      Court      Mild         Mild          Winter       Resolved     Variable      {'plans': {'crisis_plan_status': 'Not Needed', 'safety_plan_status': 'Needs Update'}, 'support_services': '', 'emergency_contact': '1', 'community_resources': 'Limited'}\\nF562      Emergency  Moderate     Severe        Variable     Resolved     Improved      {'plans': {'crisis_plan_status': 'In Place', 'safety_plan_status': 'In Place'}, 'support_services': 'Case Management,Employment,None', 'emergency_contact': '1', 'community_resources': 'Adequate'}\\n...\\n\\n\\nCREATE TABLE \\\"treatmentbasics\\\" (\\ntxkey integer NOT NULL DEFAULT nextval('treatmentbasics_txkey_seq'::regclass),\\nencref character varying NOT NULL,\\ncurmed text NULL,\\nmedadh USER-DEFINED NULL,\\nmedside USER-DEFINED NULL,\\nmedchg USER-DEFINED NULL,\\ncrisisint numeric NULL,\\ntherapy_details jsonb NULL,\\n    PRIMARY KEY (txkey),\\n    FOREIGN KEY (encref) REFERENCES encounters(enckey)\\n);\\n\\nFirst 3 rows:\\n  txkey  encref    curmed                             medadh         medside    medchg             crisisint  therapy_details\\n-------  --------  ---------------------------------  -------------  ---------  ---------------  -----------  -----------------------------------------------------------------------------------------------------------------------------\\n     17  MH485293  Antipsychotic,Antidepressant,None  Low            Moderate   Augmentation               3  {'type': 'Group', 'changes': 'Therapist Change', 'frequency': 'Weekly', 'engagement': 'Low', 'duration_months': 35}\\n     18  MH600211  Antipsychotic,None                 Medium         Severe     Dose Adjustment            1  {'type': 'CBT', 'changes': 'Modality Change', 'frequency': 'Weekly', 'engagement': 'Low', 'duration_months': 49}\\n     19  MH821921  Antipsychotic                      Non-compliant  Moderate   Switch                     3  {'type': 'Psychodynamic', 'changes': 'Modality Change', 'frequency': 'Weekly', 'engagement': 'Medium', 'duration_months': 55}\\n...\\n\\n\\nCREATE TABLE \\\"clinicians\\\" (\\nclinkey character varying NOT NULL,\\nclinconf USER-DEFINED NULL,\\nassesslim USER-DEFINED NULL,\\ndocustat USER-DEFINED NULL,\\nbillcode character varying NULL,\\nnxtrevdt date NULL,\\ncarecoord USER-DEFINED NULL,\\nrefneed USER-DEFINED NULL,\\nfuptype USER-DEFINED NULL,\\nfupfreq USER-DEFINED NULL,\\nfacconnect character varying NULL,\\n    PRIMARY KEY (clinkey),\\n    FOREIGN KEY (facconnect) REFERENCES facilities(fackey)\\n);\\n\\nFirst 3 rows:\\nclinkey    clinconf    assesslim    docustat    billcode    nxtrevdt    carecoord    refneed    fuptype    fupfreq    facconnect\\n---------  ----------  -----------  ----------  ----------  ----------  -----------  ---------  ---------  ---------  ------------\\nC8738      Medium      Cognitive    Complete    CPT90511    2025-05-09  Intensive    Services   Therapy    Weekly     F801\\nC6837      Low         Cognitive    Incomplete  CPT90696    2025-08-14  Regular   ...<truncated>"
        },
        {
          "type": "function_response",
          "name": "get_all_knowledge_definitions",
          "id": "call_H6plkGpn920sLVS40pCKL2kv",
          "response": "{\"result\": \"[\\n  {\\n    \\\"id\\\": 0,\\n    \\\"knowledge\\\": \\\"Average PHQ-9 Score by Facility (APSF)\\\",\\n    \\\"description\\\": \\\"Calculates the average PHQ-9 depression score for patients assessed at a specific facility.\\\",\\n    \\\"definition\\\": \\\"APSF = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in assessmentsymptomsandrisk} (mental\\\\\\\\_health\\\\\\\\_scores_i['depression']['phq9\\\\\\\\_score'])} {|assessmentsymptomsandrisk|}\\\"\\n  },\\n  {\\n    \\\"id\\\": 1,\\n    \\\"knowledge\\\": \\\"Average GAD-7 Score by Facility (AGSF)\\\",\\n    \\\"description\\\": \\\"Calculates the average GAD-7 anxiety score for patients assessed at a specific facility.\\\",\\n    \\\"definition\\\": \\\"AGSF = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in assessmentsymptomsandrisk} (mental\\\\\\\\_health\\\\\\\\_scores_i['anxiety']['gad7\\\\\\\\_score'])} {|assessmentsymptomsandrisk|}, \\\\\\\\text{where } mental\\\\\\\\_health\\\\\\\\_scores_i['anxiety']['gad7\\\\\\\\_score'] \\\\\\\\text{ is the GAD-7 score for each assessment in the assessmentsymptomsandrisk table, linked to a facility via encounters.facid}\\\"\\n  },\\n  {\\n    \\\"id\\\": 2,\\n    \\\"knowledge\\\": \\\"Treatment Adherence Rate (TAR)\\\",\\n    \\\"description\\\": \\\"Measures the proportion of patients with high or medium treatment adherence at a facility.\\\",\\n    \\\"definition\\\": \\\"TAR = \\\\\\\\frac{|treatmentoutcomes \\\\\\\\text{ with } txadh \\\\\\\\in \\\\\\\\{High, Medium\\\\\\\\}|} {|treatmentoutcomes|}\\\"\\n  },\\n  {\\n    \\\"id\\\": 3,\\n    \\\"knowledge\\\": \\\"Suicide Risk Prevalence (SRP)\\\",\\n    \\\"description\\\": \\\"Calculates the percentage of assessments indicating high or severe suicide risk at a facility.\\\",\\n    \\\"definition\\\": \\\"SRP = \\\\\\\\frac{|assessmentsymptomsandrisk \\\\\\\\text{ with } suicrisk \\\\\\\\in \\\\\\\\{High, Severe\\\\\\\\}|} {|assessmentsymptomsandrisk|} \\\\\\\\times 100\\\"\\n  },\\n  {\\n    \\\"id\\\": 4,\\n    \\\"knowledge\\\": \\\"Therapy Engagement Score (TES)\\\",\\n    \\\"description\\\": \\\"Computes an average engagement score across therapy sessions.\\\",\\n    \\\"definition\\\": \\\"TES = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in treatmentbasics} (therapy\\\\\\\\_details_i['engagement\\\\\\\\_score'])} {|treatmentbasics|}, \\\\\\\\text{where } engagement\\\\\\\\_score = \\\\\\\\begin{cases} 3 & \\\\\\\\text{if } therapy\\\\\\\\_details['engagement'] = High \\\\\\\\\\\\\\\\ 2 & \\\\\\\\text{if } therapy\\\\\\\\_details['engagement'] = Medium \\\\\\\\\\\\\\\\ 1 & \\\\\\\\text{if } therapy\\\\\\\\_details['engagement'] = Low \\\\\\\\\\\\\\\\ 0 & \\\\\\\\text{if } therapy\\\\\\\\_details['engagement'] = Non-compliant \\\\\\\\end{cases}, \\\\\\\\text{and } therapy\\\\\\\\_details \\\\\\\\text{ is the JSONB column in the treatmentbasics table}\\\"\\n  },\\n  {\\n    \\\"id\\\": 5,\\n    \\\"knowledge\\\": \\\"Facility Resource Adequacy Index (FRAI)\\\",\\n    \\\"description\\\": \\\"Quantifies the adequacy of community resources available at a facility.\\\",\\n    \\\"definition\\\": \\\"FRAI = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in facilities} resource\\\\\\\\_score_i} {|facilities|}, \\\\\\\\text{where } resource\\\\\\\\_score = \\\\\\\\begin{cases} 3 & \\\\\\\\text{if } support\\\\\\\\_and\\\\\\\\_resources['community\\\\\\\\_resources'] = Comprehensive \\\\\\\\\\\\\\\\ 2 & \\\\\\\\text{if } support\\\\\\\\_and\\\\\\\\_resources['community\\\\\\\\_resources'] = Adequate \\\\\\\\\\\\\\\\ 1 & \\\\\\\\text{if } support\\\\\\\\_and\\\\\\\\_resources['community\\\\\\\\_resources'] = Limited \\\\\\\\end{cases}, \\\\\\\\text{and } support\\\\\\\\_and\\\\\\\\_resources \\\\\\\\text{ is the JSONB column in the facilities table}\\\"\\n  },\\n  {\\n    \\\"id\\\": 6,\\n    \\\"knowledge\\\": \\\"Patient Functional Impairment Score (PFIS)\\\",\\n    \\\"description\\\": \\\"Calculates an average functional impairment score across patients.\\\",\\n    \\\"definition\\\": \\\"PFIS = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in assessmentsocialanddiagnosis} funcimp\\\\\\\\_score_i} {|assessmentsocialanddiagnosis|}, \\\\\\\\text{where } funcimp\\\\\\\\_score = \\\\\\\\begin{cases} 3 & \\\\\\\\text{if } funcimp = Severe \\\\\\\\\\\\\\\\ 2 & \\\\\\\\text{if } funcimp = Moderate \\\\\\\\\\\\\\\\ 1 & \\\\\\\\text{if } funcimp = Mild \\\\\\\\end{cases}\\\"\\n  },\\n  {\\n    \\\"id\\\": 7,\\n    \\\"knowledge\\\": \\\"Crisis Intervention Frequency (CIF)\\\",\\n    \\\"description\\\": \\\"Measures the average number of crisis interventions per patient at a facility.\\\",\\n    \\\"definition\\\": \\\"CIF = \\\\\\\\frac{\\\\\\\\sum_{i \\\\\\\\in treatmentb...<truncated>"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "ask_user",
          "id": "call_hzIfcc2sG4OuyniVisEVNEJX",
          "args": {
            "question": "Does “prevalence over 20%” mean Suicide Risk Prevalence (assessments with High or Severe suicide risk), or the broader High-Risk Patient definition that also includes PHQ-9 or GAD-7 scores over 15?"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "ask_user",
          "id": "call_hzIfcc2sG4OuyniVisEVNEJX",
          "response": "{\"result\": \"“Prevalence over 20%” refers specifically to Suicide Risk Prevalence — the percentage of assessments with High or Severe suicide risk. It does not include the broader high-risk patient definition based on PHQ-9 or GAD-7 scores over 15.\\n\\n[SYSTEM NOTE: Remaining budget: 14.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "ask_user",
          "id": "call_OJRmmsb97YiY2zqp6HF19nNx",
          "args": {
            "question": "What formula should I use for Resource-Demand Differential (RDD)? It is referenced in the available definitions, but its formula is not provided."
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "ask_user",
          "id": "call_OJRmmsb97YiY2zqp6HF19nNx",
          "response": "{\"result\": \"The Resource-Demand Differential (RDD) is calculated as the difference between the Patient Functional Impairment Score (PFIS) and the Facility Resource Adequacy Index (FRAI): RDD = PFIS − FRAI. A higher RDD indicates a greater gap between patient needs and available facility resources.\\n\\n[SYSTEM NOTE: Remaining budget: 12.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "ask_user",
          "id": "call_MIcgRMOEvowKt4EdhrxFTDCr",
          "args": {
            "question": "How many top facilities should I list, ranked by highest RDD?"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "ask_user",
          "id": "call_MIcgRMOEvowKt4EdhrxFTDCr",
          "response": "{\"result\": \"The task specifies listing the top 100 facilities ranked by highest RDD (Resource-Demand Differential). So you should show up to 100 facilities, ordered by RDD from highest to lowest.\\n\\n[SYSTEM NOTE: Remaining budget: 10.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "execute_sql",
          "id": "call_JwbGtw8Ww45GY2rwUQ1jUWsv",
          "args": {
            "sql": "WITH risk AS (\n    SELECT e.facid,\n           100.0 * COUNT(*) FILTER (WHERE r.suicrisk IN ('High', 'Severe')) / COUNT(*) AS srp\n    FROM encounters e\n    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\n    GROUP BY e.facid\n), impairment AS (\n    SELECT e.facid,\n           AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 END) AS pfis\n    FROM encounters e\n    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\n    GROUP BY e.facid\n), scores AS (\n    SELECT f.fackey AS facility_id, i.pfis,\n           CASE f.support_and_resources ->> 'community_resources'\n               WHEN 'Comprehensive' THEN 3\n               WHEN 'Adequate' THEN 2\n               WHEN 'Limited' THEN 1\n           END AS frai\n    FROM facilities f\n    JOIN risk r ON r.facid = f.fackey\n    JOIN impairment i ON i.facid = f.fackey\n    WHERE r.srp > 20\n)\nSELECT facility_id, pfis, frai, pfis - frai AS rdd\nFROM scores\nORDER BY rdd DESC, facility_id\nLIMIT 100;"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "execute_sql",
          "id": "call_JwbGtw8Ww45GY2rwUQ1jUWsv",
          "response": "{\"result\": \"facility_id | pfis | frai | rdd ------------------------------- F105 | 3.0000000000000000 | 1 | 2.0000000000000000 F123 | 3.0000000000000000 | 1 | 2.0000000000000000 F131 | 3.0000000000000000 | 1 | 2.0000000000000000 F152 | 3.0000000000000000 | 1 | 2.0000000000000000 F167 | 3.0000000000000000 | 1 | 2.0000000000000000 F184 | 3.0000000000000000 | 1 | 2.0000000000000000 F218 | 3.0000000000000000 | 1 | 2.0000000000000000 F228 | 3.0000000000000000 | 1 | 2.0000000000000000 F247 | 3.0000000000000000 | 1 | 2.0000000000000000 F248 | 3.0000000000000000 | 1 | 2.0000000000000000 F282 | 3.0000000000000000 | 1 | 2.0000000000000000 F289 | 3.0000000000000000 | 1 | 2.0000000000000000 F324 | 3.0000000000000000 | 1 | 2.0000000000000000 F351 | 3.0000000000000000 | 1 | 2.0000000000000000 F383 | 3.0000000000000000 | 1 | 2.0000000000000000 F452 | 3.0000000000000000 | 1 | 2.0000000000000000 F460 | 3.0000000000000000 | 1 | 2.0000000000000000 F559 | 3.0000000000000000 | 1 | 2.0000000000000000 F703 | 3.0000000000000000 | 1 | 2.0000000000000000 F719 | 3.0000000000000000 | 1 | 2.0000000000000000 F743 | 3.0000000000000000 | 1 | 2.0000000000000000 F755 | 3.0000000000000000 | 1 | 2.0000000000000000 F906 | 3.0000000000000000 | 1 | 2.0000000000000000 F915 | 3.0000000000000000 | 1 | 2.0000000000000000 F919 | 3.0000000000000000 | 1 | 2.0000000000000000 F944 | 3.0000000000000000 | 1 | 2.0000000000000000 F990 | 3.0000000000000000 | 1 | 2.0000000000000000 F991 | 3.0000000000000000 | 1 | 2.0000000000000000 F156 | 2.6666666666666667 | 1 | 1.6666666666666667 F163 | 2.5000000000000000 | 1 | 1.5000000000000000 F309 | 2.5000000000000000 | 1 | 1.5000000000000000 F335 | 2.5000000000000000 | 1 | 1.5000000000000000 F393 | 2.5000000000000000 | 1 | 1.5000000000000000 F439 | 2.5000000000000000 | 1 | 1.5000000000000000 F450 | 2.5000000000000000 | 1 | 1.5000000000000000 F650 | 2.5000000000000000 | 1 | 1.5000000000000000 F941 | 2.5000000000000000 | 1 | 1.5000000000000000 F284 | 2.3333333333333333 | 1 | 1.3333333333333333 F457 | 2.3333333333333333 | 1 | 1.3333333333333333 F788 | 2.3333333333333333 | 1 | 1.3333333333333333 F804 | 2.3333333333333333 | 1 | 1.3333333333333333 F494 | 2.2500000000000000 | 1 | 1.2500000000000000 F960 | 2.2500000000000000 | 1 | 1.2500000000000000 F112 | 2.0000000000000000 | 1 | 1.0000000000000000 F129 | 2.0000000000000000 | 1 | 1.0000000000000000 F138 | 2.0000000000000000 | 1 | 1.0000000000000000 F146 | 2.0000000000000000 | 1 | 1.0000000000000000 F176 | 2.0000000000000000 | 1 | 1.0000000000000000 F203 | 3.0000000000000000 | 2 | 1.0000000000000000 F230 | 2.0000000000000000 | 1 | 1.0000000000000000 F272 | 2.0000000000000000 | 1 | 1.0000000000000000 F293 | 2.0000000000000000 | 1 | 1.0000000000000000 F297 | 3.0000000000000000 | 2 | 1.0000000000000000 F302 | 2.0000000000000000 | 1 | 1.0000000000000000 F303 | 2.0000000000000000 | 1 | 1.0000000000000000 F322 | 2.0000000000000000 | 1 | 1.0000000000000000 F327 | 2.0000000000000000 | 1 | 1.0000000000000000 F348 | 3.0000000000000000 | 2 | 1.0000000000000000 F349 | 2.0000000000000000 | 1 | 1.0000000000000000 F361 | 2.0000000000000000 | 1 | 1.0000000000000000 F375 | 2.0000000000000000 | 1 | 1.0000000000000000 F377 | 2.0000000000000000 | 1 | 1.0000000000000000 F380 | 2.0000000000000000 | 1 | 1.0000000000000000 F417 | 3.0000000000000000 | 2 | 1.0000000000000000 F420 | 2.0000000000000000 | 1 | 1.0000000000000000 F421 | 2.0000000000000000 | 1 | 1.0000000000000000 F444 | 2.0000000000000000 | 1 | 1.0000000000000000 F468 | 2.0000000000000000 | 1 | 1.0000000000000000 F473 | 2.0000000000000000 | 1 | 1.0000000000000000 F499 | 3.0000000000000000 | 2 | 1.0000000000000000 F506 |...\\n\\n[SYSTEM NOTE: Remaining budget: 9.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "submit_sql",
          "id": "call_XRcFQf3QzTHb4F4DssZtWNeu",
          "args": {
            "sql": "WITH risk AS (\n    SELECT e.facid,\n           100.0 * COUNT(*) FILTER (WHERE r.suicrisk IN ('High', 'Severe')) / COUNT(*) AS srp\n    FROM encounters e\n    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\n    GROUP BY e.facid\n), impairment AS (\n    SELECT e.facid,\n           AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 END) AS pfis\n    FROM encounters e\n    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\n    GROUP BY e.facid\n), scores AS (\n    SELECT f.fackey AS facility_id, i.pfis,\n           CASE f.support_and_resources ->> 'community_resources'\n               WHEN 'Comprehensive' THEN 3\n               WHEN 'Adequate' THEN 2\n               WHEN 'Limited' THEN 1\n           END AS frai\n    FROM facilities f\n    JOIN risk r ON r.facid = f.fackey\n    JOIN impairment i ON i.facid = f.fackey\n    WHERE r.srp > 20\n)\nSELECT facility_id, pfis, frai, pfis - frai AS rdd\nFROM scores\nORDER BY rdd DESC, facility_id\nLIMIT 100;"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "submit_sql",
          "id": "call_XRcFQf3QzTHb4F4DssZtWNeu",
          "response": "{\"result\": \"SQL failed Phase 1. Your SQL is not correct.\\nBudget remaining: 6.0 bird-coins\\n\\n[SYSTEM NOTE: Remaining budget: 6.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "execute_sql",
          "id": "call_9HS7hKaiqyRbO72BoLODPvFt",
          "args": {
            "sql": "SELECT funcimp::text, COUNT(*) FROM assessmentsocialanddiagnosis GROUP BY funcimp; SELECT COUNT(*) AS encounters, COUNT(DISTINCT abref) AS assessments FROM encounters; SELECT COUNT(*) FROM encounters e JOIN assessmentsymptomsandrisk r ON r.asrkey=e.abref LEFT JOIN assessmentsocialanddiagnosis d ON d.asdkey=e.abref WHERE d.asdkey IS NULL;"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "execute_sql",
          "id": "call_9HS7hKaiqyRbO72BoLODPvFt",
          "response": "{\"result\": \"count\\n-----\\n0\\n\\n[SYSTEM NOTE: Remaining budget: 5.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "execute_sql",
          "id": "call_CGRHs28ORy0WmoLAOQ8A0yQ6",
          "args": {
            "sql": "SELECT 'funcimp' AS kind, funcimp::text AS value, COUNT(*) AS n FROM assessmentsocialanddiagnosis GROUP BY funcimp UNION ALL SELECT 'resources', support_and_resources->>'community_resources', COUNT(*) FROM facilities GROUP BY support_and_resources->>'community_resources' UNION ALL SELECT 'encounters', 'distinct assessments', COUNT(DISTINCT abref) FROM encounters UNION ALL SELECT 'encounters', 'total', COUNT(*) FROM encounters;"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "execute_sql",
          "id": "call_CGRHs28ORy0WmoLAOQ8A0yQ6",
          "response": "{\"result\": \"kind | value | n\\n----------------\\nfuncimp | Moderate | 252\\nfuncimp | Severe | 252\\nfuncimp | Mild | 495\\nresources | Comprehensive | 159\\nresources | Limited | 308\\nresources | Adequate | 128\\nencounters | distinct assessments | 998\\nencounters | total | 999\\n\\n[SYSTEM NOTE: Remaining budget: 4.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "function_call",
          "name": "submit_sql",
          "id": "call_FanAavZTb8aO0nvny5OCx3X9",
          "args": {
            "sql": "SELECT f.fackey,\n       AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 ELSE 0 END) AS pfis,\n       AVG(CASE f.support_and_resources ->> 'community_resources' WHEN 'Comprehensive' THEN 3 WHEN 'Adequate' THEN 2 WHEN 'Limited' THEN 1 ELSE 0 END) AS frai,\n       AVG(CASE d.funcimp WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 WHEN 'Mild' THEN 1 ELSE 0 END)\n       - AVG(CASE f.support_and_resources ->> 'community_resources' WHEN 'Comprehensive' THEN 3 WHEN 'Adequate' THEN 2 WHEN 'Limited' THEN 1 ELSE 0 END) AS rdd\nFROM facilities f\nJOIN encounters e ON e.facid = f.fackey\nJOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\nJOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\nGROUP BY f.fackey\nHAVING 100.0 * SUM(CASE WHEN r.suicrisk IN ('High', 'Severe') THEN 1 ELSE 0 END) / COUNT(*) > 20\nORDER BY rdd DESC\nLIMIT 100;"
          }
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": false,
    "content": {
      "role": "user",
      "parts": [
        {
          "type": "function_response",
          "name": "submit_sql",
          "id": "call_FanAavZTb8aO0nvny5OCx3X9",
          "response": "{\"result\": \"Phase 1 correct! (Reward: 0.7). Moving to Phase 2.\\nReward: 0.7\\nFollow-up question: Also show Facility Risk Profile Index in the end.\\nBudget remaining: 1.0 bird-coins\\n\\n[SYSTEM NOTE: Remaining budget: 1.0/18.0]\"}"
        }
      ]
    }
  },
  {
    "type": "adk_event",
    "author": "bird_interact_agent",
    "invocation_id": "e-e0662505-c7b5-4b02-b0fb-91236ea271de",
    "branch": null,
    "final": true,
    "content": {
      "role": "model",
      "parts": [
        {
          "type": "text",
          "text": "```sql\nWITH scores AS (\n    SELECT\n        f.fackey AS facility_id,\n        AVG(CASE d.funcimp\n            WHEN 'Severe' THEN 3\n            WHEN 'Moderate' THEN 2\n            WHEN 'Mild' THEN 1\n            ELSE 0\n        END) AS pfis,\n        AVG(CASE f.support_and_resources ->> 'community_resources'\n            WHEN 'Comprehensive' THEN 3\n            WHEN 'Adequate' THEN 2\n            WHEN 'Limited' THEN 1\n            ELSE 0\n        END) AS frai,\n        100.0 * SUM(CASE\n            WHEN r.suicrisk IN ('High', 'Severe') THEN 1\n            ELSE 0\n        END) / COUNT(*) AS srp\n    FROM facilities f\n    JOIN encounters e ON e.facid = f.fackey\n    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref\n    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref\n    GROUP BY f.fackey\n)\nSELECT\n    facility_id,\n    pfis,\n    frai,\n    pfis - frai AS rdd,\n    (srp / 100.0) * 5 + pfis AS frpi\nFROM scores\nWHERE srp > 20\nORDER BY rdd DESC\nLIMIT 100;\n```"
        }
      ]
    }
  }
]
````

## final_response

````text
```sql
WITH scores AS (
    SELECT
        f.fackey AS facility_id,
        AVG(CASE d.funcimp
            WHEN 'Severe' THEN 3
            WHEN 'Moderate' THEN 2
            WHEN 'Mild' THEN 1
            ELSE 0
        END) AS pfis,
        AVG(CASE f.support_and_resources ->> 'community_resources'
            WHEN 'Comprehensive' THEN 3
            WHEN 'Adequate' THEN 2
            WHEN 'Limited' THEN 1
            ELSE 0
        END) AS frai,
        100.0 * SUM(CASE
            WHEN r.suicrisk IN ('High', 'Severe') THEN 1
            ELSE 0
        END) / COUNT(*) AS srp
    FROM facilities f
    JOIN encounters e ON e.facid = f.fackey
    JOIN assessmentsymptomsandrisk r ON r.asrkey = e.abref
    JOIN assessmentsocialanddiagnosis d ON d.asdkey = e.abref
    GROUP BY f.fackey
)
SELECT
    facility_id,
    pfis,
    frai,
    pfis - frai AS rdd,
    (srp / 100.0) * 5 + pfis AS frpi
FROM scores
WHERE srp > 20
ORDER BY rdd DESC
LIMIT 100;
```
````

