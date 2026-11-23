-- Requêtes Athena sur les logs CloudTrail du projet 1.
-- Étape 1 : créer la table. Le plus simple : console CloudTrail > Event history >
-- "Create Athena table", en choisissant le bucket de logs. Remplace ensuite
-- cloudtrail_logs par le nom de table généré.

-- Qui a modifié des policies IAM ces 7 derniers jours ?
SELECT eventtime, useridentity.arn AS actor, eventname, sourceipaddress,
       json_extract_scalar(requestparameters, '$.policyArn') AS policy
FROM cloudtrail_logs
WHERE eventsource = 'iam.amazonaws.com'
  AND eventname IN ('CreatePolicyVersion', 'SetDefaultPolicyVersion',
                    'AttachUserPolicy', 'AttachRolePolicy', 'PutUserPolicy', 'PutRolePolicy')
  AND from_iso8601_timestamp(eventtime) > current_timestamp - interval '7' day
ORDER BY eventtime DESC;

-- Principaux avec le plus d'AccessDenied (signe d'énumération)
SELECT useridentity.arn AS actor, count(*) AS denied, count(DISTINCT eventname) AS distinct_apis
FROM cloudtrail_logs
WHERE errorcode IN ('AccessDenied', 'Client.UnauthorizedOperation', 'AccessDeniedException')
GROUP BY useridentity.arn
HAVING count(*) > 20
ORDER BY denied DESC;

-- Même clé d'accès utilisée depuis plusieurs IP
SELECT useridentity.accesskeyid AS key_id, useridentity.arn AS actor,
       count(DISTINCT sourceipaddress) AS ips, array_agg(DISTINCT sourceipaddress) AS ip_list
FROM cloudtrail_logs
WHERE useridentity.accesskeyid IS NOT NULL
  AND sourceipaddress NOT LIKE '%.amazonaws.com'
GROUP BY useridentity.accesskeyid, useridentity.arn
HAVING count(DISTINCT sourceipaddress) > 1;

-- Tentatives de désactivation de la journalisation ou de la détection
SELECT eventtime, useridentity.arn, eventname, errorcode
FROM cloudtrail_logs
WHERE eventname IN ('StopLogging', 'DeleteTrail', 'UpdateTrail', 'PutEventSelectors',
                    'DeleteDetector', 'DisassociateFromMasterAccount', 'DeleteFlowLogs')
ORDER BY eventtime DESC;
