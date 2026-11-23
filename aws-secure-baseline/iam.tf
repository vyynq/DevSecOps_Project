# ---------------------------------------------------------------------------
# Identité : politique de mot de passe, rôle d'audit protégé par MFA,
# IAM Access Analyzer (détecte les ressources partagées hors du compte).
# ---------------------------------------------------------------------------

resource "aws_iam_account_password_policy" "strict" {
  minimum_password_length        = 14
  require_lowercase_characters   = true
  require_uppercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  allow_users_to_change_password = true
  password_reuse_prevention      = 24
  max_password_age               = 90
}

# Qui peut assumer le rôle : uniquement des identités de CE compte,
# et uniquement si elles se sont authentifiées avec MFA il y a moins d'1 h.
data "aws_iam_policy_document" "auditor_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["true"]
    }
    condition {
      test     = "NumericLessThan"
      variable = "aws:MultiFactorAuthAge"
      values   = ["3600"]
    }
  }
}

resource "aws_iam_role" "auditor" {
  name                 = "${local.name}-auditor"
  description          = "Lecture seule de la configuration de sécurité, MFA obligatoire"
  assume_role_policy   = data.aws_iam_policy_document.auditor_trust.json
  max_session_duration = 3600
}

# Politique managée AWS : lit la configuration de sécurité de tous les services,
# sans accès aux données (pas de s3:GetObject).
resource "aws_iam_role_policy_attachment" "auditor_security_audit" {
  role       = aws_iam_role.auditor.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}

resource "aws_accessanalyzer_analyzer" "account" {
  analyzer_name = "${local.name}-analyzer"
  type          = "ACCOUNT"
}
