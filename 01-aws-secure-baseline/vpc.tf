# ---------------------------------------------------------------------------
# Réseau : 1 VPC, 2 zones de disponibilité, subnets publics et privés.
# Pas de NAT Gateway (≈35 $/mois) : les subnets privés n'ont AUCUNE route
# vers Internet. C'est aussi la configuration la plus sûre par défaut.
# ---------------------------------------------------------------------------

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-igw" }
}

# 10.0.0.0/24, 10.0.1.0/24
resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false # une IP publique doit être un choix explicite

  tags = { Name = "${local.name}-public-${local.azs[count.index]}", Tier = "public" }
}

# 10.0.10.0/24, 10.0.11.0/24
resource "aws_subnet" "private" {
  count             = length(local.azs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = local.azs[count.index]

  tags = { Name = "${local.name}-private-${local.azs[count.index]}", Tier = "private" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name}-rt-public" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Table privée : uniquement la route locale implicite du VPC.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-rt-private" }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Le security group par défaut autorise tout le trafic interne au groupe.
# En le "prenant en main" sans règles, on le vide : deny all.
resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-default-sg-locked" }
}

# Journal de tout le trafic réseau (acceptés ET refusés) vers le bucket de logs.
resource "aws_flow_log" "vpc" {
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  log_destination_type = "s3"
  log_destination      = "${aws_s3_bucket.logs.arn}/vpc-flow-logs/"

  depends_on = [aws_s3_bucket_policy.logs]
}
