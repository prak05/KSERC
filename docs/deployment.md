# Deployment

Two ways to run the engine. Both use the same image and code; one variable (`CLOUD`) decides where state and models live.

| | Local | AWS |
|---|---|---|
| Compute | your machine (`make run`) or Docker (`make up`) | ECS Fargate behind an Application Load Balancer |
| Model | Ollama / LM Studio / llama.cpp (`LLM_PROVIDER=local`) or `offline` | Claude on Amazon Bedrock |
| Tables from petitions | PyMuPDF table finder | Amazon Textract (`StartDocumentAnalysis`, TABLES) |
| Document store | SQLite (`data/store.sqlite3`) | DynamoDB (one table, `pk`/`sk`) — bodies over 350 KB spill to S3 |
| Regulatory corpus | `documents/` | S3 `s3://<bucket>/documents/`, mirrored into the task at start-up |
| Credentials | none | the ECS task role — no keys anywhere |

## Local

```bash
make setup          # venv, npm ci, .env from .env.example
make run            # builds the UI, serves UI + API on http://localhost:8000
make dev            # API with reload on :8000 + Vite on :3000
make up             # Docker: app + Ollama on http://localhost:8080
docker compose exec ollama ollama pull qwen2.5:14b   # first run only
```

Use `LLM_PROVIDER=offline` to run without any model: extraction falls back to PyMuPDF and the deterministic rules engine still produces the audit; model-drafted prose is left empty.

To use Claude from your laptop instead, set `LLM_PROVIDER=bedrock` and make sure your AWS profile can call Bedrock in `BEDROCK_REGION`.

## AWS

Prerequisites: Terraform ≥ 1.6, Docker, AWS CLI v2 signed in to the target account, and **model access for Claude enabled in Amazon Bedrock** for the region you set as `bedrock_region`.

```bash
make plan-aws REGION=ap-south-1      # review what will be created (28 resources)
make deploy-aws REGION=ap-south-1    # apply → build & push image → sync corpus → roll out
```

`scripts/deploy-aws.sh` prints the URL when the service is stable.

### What gets created (`infra/aws/main.tf`)

- VPC with two public subnets (tasks get public IPs, so there is no NAT gateway to pay for)
- Application Load Balancer, idle timeout 900 s (order drafting can take minutes); HTTPS when `certificate_arn` is set
- ECS cluster + Fargate service (2 vCPU / 4 GB, 50 GB ephemeral storage), CloudWatch logs (30 days)
- ECR repository (scan on push, keeps the last 10 images)
- S3 bucket — private, versioned, encrypted; `textract-input/` expires after 7 days
- DynamoDB table — on-demand, point-in-time recovery, encrypted
- IAM task role limited to that bucket, that table, Textract analysis and Bedrock in one region

### Settings worth changing (`infra/aws/example.tfvars`)

- `allowed_cidrs` — restrict the load balancer to the Commission's network
- `certificate_arn` — an ACM certificate to serve HTTPS
- `bedrock_region` — if Claude access is enabled in a different region from the app
- `llm_model` / `llm_fallback_model` — defaults `anthropic.claude-opus-5-5` / `anthropic.claude-opus-4-8`

Keep `desired_count = 1`: an analysis runs inside the task that accepted it.

### Tear down

```bash
make destroy-aws REGION=ap-south-1
```

The bucket and registry are protected from deletion while non-empty unless `force_destroy = true`.
