# Deploying Noise on AWS

This guide deploys a new, independent Noise instance on Ubuntu 24.04 LTS EC2.
Docker Compose runs Django/Gunicorn and Caddy. Caddy provides automatic HTTPS;
only Caddy publishes ports. By default, SQLite and uploads persist in a Docker
volume on the instance's EBS disk. S3 and RDS are optional additions.

You need an AWS account, a domain you control, SSH access, and your Noise GitHub
repository URL. Replace every example hostname, repository URL, email, and AWS
resource name below with your own. Provisioning AWS resources can incur charges.

## 1. Create the instance and DNS record

In the EC2 console, launch Ubuntu Server 24.04 LTS on a small instance with
roughly 2 GiB RAM (for example, `t3.small`) and an encrypted EBS root volume with
enough space for your uploads and backups. Enable EBS snapshots or an AWS Backup
plan. This single-instance setup has downtime during maintenance and does not
provide automatic failover.

Configure its security group:

| Port | Source | Purpose |
| --- | --- | --- |
| TCP 22 | Your administrator IP only | SSH |
| TCP 80 | Internet | HTTP redirects and certificate validation |
| TCP 443 | Internet | HTTPS |

Allow outbound DNS and HTTPS for package/image downloads, certificate issuance,
and optional external services. Do not open 8000 or database ports publicly.
If you enable IPv6, configure equivalent IPv6 rules.

Associate an Elastic IP and point an A record such as `noise.example.com` to it.
Only publish an AAAA record if IPv6 is configured and reachable. Wait until DNS
resolves to the instance before starting Caddy. For the initial setup, use a
direct DNS record; if you later add Cloudflare proxying, use Full (strict) TLS.
This configuration assumes Caddy is the public TLS endpoint, not an ALB.

Connect with your own key and address:

```sh
ssh -i /path/to/your-key.pem ubuntu@YOUR_ELASTIC_IP
```

## 2. Install Docker and clone Noise

On the fresh Ubuntu 24.04 instance, install Docker Engine and the Compose plugin
using [Docker's official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
The following commands configure the official repository for Ubuntu 24.04:

```sh
sudo apt update
sudo apt install -y ca-certificates curl git openssl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker compose version
```

Clone Noise, or substitute your fork's repository URL:

```sh
git clone https://github.com/darrell-d/noise.git noise
cd noise
cp .env.aws.example .env
chmod 600 .env
openssl rand -hex 48
```

## 3. Configure the environment

Edit `.env` with an editor such as `nano .env`. Paste the generated signing secret
into `SECRET_KEY`, and fill in these values consistently:

```dotenv
SITE_DOMAIN=noise.example.com
ACME_EMAIL=you@example.com
ALLOWED_HOSTS=noise.example.com
PUBLIC_URL=https://noise.example.com
CSRF_TRUSTED_ORIGINS=https://noise.example.com
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=you@example.com
DJANGO_SUPERUSER_PASSWORD=YOUR_UNIQUE_STRONG_PASSWORD
```

`SITE_DOMAIN` is a hostname, without `https://` or a path. `ACME_EMAIL` is the
certificate contact address. Keep the generated `SECRET_KEY` private and stable
across restarts. Keep the HTTPS/cookie/proxy flags from `.env.aws.example` enabled,
`DEBUG=false`, and `WEB_CONCURRENCY=1` for SQLite. Leave `DB_HOST` and
`AWS_STORAGE_BUCKET_NAME` blank for the default local storage setup.

The AWS Compose file overrides the internal bind address, port, and data path.
Gunicorn is reachable only inside Docker's network. Caddy replaces forwarding
headers, so enabling `TRUST_PROXY_HTTPS` is appropriate for this topology.

## 4. Start the application

From the repository directory on EC2:

```sh
sudo docker compose -f compose.aws.yaml config --quiet
sudo docker compose -f compose.aws.yaml up --build -d
sudo docker compose -f compose.aws.yaml ps
sudo docker compose -f compose.aws.yaml logs --tail=100 noise caddy
```

The app applies migrations, collects static assets, and creates the first
administrator. Caddy obtains and renews its certificate automatically once DNS
and ports 80/443 are reachable. Certificates persist in `caddy-data`; see the
[Caddy Docker documentation](https://caddyserver.com/docs/running#docker-compose).

Visit `https://noise.example.com/noise/` and log in. Visit `/admin/` to manage
readers and groups. After the initial account is created, remove the password
from `.env` and recreate the app container to discard it from its environment:

```sh
sudo docker compose -f compose.aws.yaml up -d --force-recreate noise
curl --fail --head https://noise.example.com/noise/
```

Docker starts at boot, and the containers use `restart: unless-stopped`.
No separate systemd service is needed. Keep the `noise-data`, `caddy-data`, and
`caddy-config` volumes. Do not run `down -v` on an instance whose data you need.

## Optional: private S3 uploads

Create a dedicated S3 bucket in your chosen region. Keep **Block Public Access**
enabled and **Object Ownership: Bucket owner enforced** (ACLs disabled). Noise
does not send object ACLs; it uses private objects and five-minute signed URLs.
See [S3 Object Ownership](https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html).

Attach an IAM role to the EC2 instance. For a bucket named `YOUR_NOISE_BUCKET`,
use an identity policy scoped to that bucket and Noise's upload prefix:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_NOISE_BUCKET"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR_NOISE_BUCKET/noise/*"
    }
  ]
}
```

Use default S3-managed encryption for this example. A customer-managed KMS key
also needs suitable KMS permissions and key policy. Enable bucket versioning or
another backup policy; instance snapshots do not back up S3 objects.

Require IMDSv2 on the EC2 instance and set its metadata response hop limit to 2
so the app container can obtain role credentials. See AWS's
[instance metadata options](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html).
Do not put long-lived AWS access keys in `.env`. Set:

```dotenv
AWS_STORAGE_BUCKET_NAME=YOUR_NOISE_BUCKET
AWS_S3_REGION_NAME=us-east-1
```

Use the bucket's actual region. Leave `AWS_S3_ENDPOINT_URL` blank for AWS S3.
Recreate the app with the same `up -d --force-recreate noise` command. Test both
public and restricted uploads. Existing local uploads are not copied to S3 by
changing the setting; move them separately before switching a populated site.
The database still needs its own backup.

## Optional: RDS PostgreSQL

For a larger installation, create an RDS PostgreSQL instance in the same VPC,
with public access disabled, encryption and automated backups enabled, an initial
database named `noise`, and a database account dedicated to this application.
Allow inbound TCP 5432 on the RDS security group **only from the EC2 security
group**. Use the RDS DNS endpoint, rather than an IP address.

Download the AWS CA bundle on the EC2 host into the mounted `deploy/` directory:

```sh
curl --fail --silent --show-error https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o deploy/rds-global-bundle.pem
```

Configure your connection values:

```dotenv
DB_HOST=YOUR_RDS_ENDPOINT
DB_PORT=5432
DB_NAME=noise
DB_USER=YOUR_APP_DATABASE_USER
DB_PASSWORD=YOUR_DATABASE_PASSWORD
DB_SSLMODE=verify-full
PGSSLROOTCERT=/app/deploy/rds-global-bundle.pem
WEB_CONCURRENCY=2
```

The bind mount makes the certificate bundle available inside the app container;
`PGSSLROOTCERT` is read by PostgreSQL's client library. See AWS's
[PostgreSQL SSL instructions](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).
Recreate the app; startup applies migrations to the selected database. A new RDS
database starts empty, including users. Changing `DB_HOST` does not migrate
SQLite content; plan an export/import before changing an existing site.
Initial administrator credentials must be supplied for a new empty database.

## Backups and upgrades

For the default SQLite/local uploads deployment, pause app writes and copy the
data directory from the existing container. Run from the repository directory:

```sh
mkdir -p backups
sudo docker compose -f compose.aws.yaml stop noise
sudo docker compose -f compose.aws.yaml cp noise:/app/data "./backups/data-$(date -u +%Y%m%dT%H%M%SZ)"
sudo docker compose -f compose.aws.yaml start noise
```

Copy the backup and `.env` to private storage outside this instance. Backups
contain private posts and uploads. Also preserve Caddy's data volume when moving
the deployment. For RDS/S3, use RDS backups and bucket versioning/backup policies;
the directory copy does not capture those services. Test restoration periodically.

Before an upgrade, take a backup and review the release changes. From a clean
checkout of your deployment branch:

```sh
git pull --ff-only
sudo docker compose -f compose.aws.yaml up --build -d
sudo docker compose -f compose.aws.yaml logs --tail=100 noise
```

Startup applies database migrations automatically. Rolling back an image does
not undo migrations; restoring a compatible backup may be necessary. Local
changes should be preserved on your fork before pulling upgrades.

## Troubleshooting

- **Certificate failure:** check A/AAAA records, security-group ports 80/443,
  `SITE_DOMAIN`, and Caddy logs. A broken AAAA record can prevent validation.
- **502:** inspect app logs for a missing secret, missing initial administrator
  password, migration error, database connection failure, or unreadable volume.
- **400:** match `ALLOWED_HOSTS` to the requested hostname.
- **CSRF/login failure:** match the HTTPS `PUBLIC_URL` and
  `CSRF_TRUSTED_ORIGINS`; verify the HTTPS/cookie/proxy settings.
- **413:** the app defaults to 95 MiB per request; Caddy allows a 100 MB body.
  If you increase `NOISE_MAX_UPLOAD_BYTES`, increase Caddy's `max_size` too.
- **S3 access failure:** check the bucket region, IAM role/policy, IMDSv2 hop
  limit, and outbound access to S3. Keep ACLs disabled and the bucket private.
- **RDS TLS failure:** check the DNS endpoint, current CA bundle, mounted bundle
  path, security group, and `DB_SSLMODE=verify-full`.
