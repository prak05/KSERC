<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# KSERC Archives and Links Reference for RAG

This Markdown file compiles key links and data from KSERC (Kerala State Electricity Regulatory Commission) archives, petitions, and related regulatory documents. Use this as a reference document for your **RAG (Retrieval-Augmented Generation)** pipeline to ingest into the Vector Database. It includes unstructured legal texts, historical orders for truing-up, and inflation indices.

**Purpose for RAG**:

- Chunk and embed these links' content for legal compliance checks (e.g., Regulation 73(3)).
- Reference historical trends for Forensic Auditor agent.
- Populate SQL DB schemas from orders (ARR norms vs. actuals).
- Train agents on KSERC orders for controllability logic (Tariff Regulations 2021).

**Last Updated**: February 21, 2026
**Source**: Official KSERC sites (erckerala.org, dev.erckerala.org) and government portals.

## 1. Core Legal Texts (Vector DB Ingestion)

| Document | Description | Direct Download Link | Notes |
| :-- | :-- | :-- | :-- |
| Electricity Act, 2003 | Full Act from Ministry of Law (India Code) | [PDF](https://www.indiacode.nic.in/bitstream/123456789/15367/1/the_electricity_act,_2003.pdf) | Primary law; ingest all sections [^1] |
| KSERC Tariff Regulations, 2021 | Official notified regulations (incl. Reg 73(3) on distribution losses) | [PDF](https://infopark.in/download_files/documents/Tariff%20Regulation%20-%202021_650.pdf) | Encode for Legal Brain agent [^2] |
| KSERC Reg 73(3) Example Order | Distribution loss variation methodology | [PDF](https://dev.erckerala.org/api/storage/orders/U3oNn70VOOdrzVu36nJWLNuiZhOYf1qI5cI8zlMW.pdf) | Compliance check reference [^3] |

## 2. Historical Truing-Up Data \& Orders (SQL DB Population)

Browse full archives for bulk download:

- Petitions Page: https://www.erckerala.org/petitionpage (filter "Truing up")[^4]
- Archives Page: https://www.erckerala.org/archives[^5]

| Year/Case | Description | Direct Link | Key Data for Trends |
| :-- | :-- | :-- | :-- |
| 2021-22 Truing-Up | Petition/Order with ARR/expenditure | [PDF](https://dev.erckerala.org/api/storage/orders/MlU8Gvcqr8SvS1pUiPXdAIrlSHvkLTpnYqVnSY6q.pdf) | Historical averages [^6] |
| 2023 Order | Tariff/Truing-up decision | [PDF](https://dev.erckerala.org/api/storage/orders/TqduE3KQeTcfSdPqmY6Ssvtvx1Hw6ajGFdCzznFY.pdf) | Deviation analysis [^7] |
| Recent Tariff Order | Analysis \& prudence checks | [PDF](https://dev.erckerala.org/api/storage/orders/EteXjfGVGqYjfUJRfMbQa93a8iC1nbiu3ZnzLm7e.pdf) | Fine-tune on decisions [^8] |
| 2016-17 F\&T Order | Legacy truing-up (No. 1007) | [PDF](https://dev.erckerala.org/api/storage/orders/F7KYDIEOOQH5rLT0wB6zHXpgbM0PGSRebLoJZOae.pdf) | Long-term trends [^9] |
| 2023-24 Order | Recent losses/expenses | [PDF](https://dev.erckerala.org/api/storage/orders/RGERp8UeMg7jybGlLDEXtCsFqlQ7X5WdAQE73DJl.pdf) | CPI/WPI adjustments [^10] |

**RAG Instruction**: Ingest all PDFs via chunking (e.g., 500-token sections). Extract tables for SQL (e.g., approved ARR vs. actuals).

## 3. Inflation Indices (CPI/WPI for SQL DB)

| Index | Period | Download/Source | Usage |
| :-- | :-- | :-- | :-- |
| CPI Historical | 2013-2026 (monthly) | [Table/CSV](https://www.rateinflation.com/consumer-price-index/india-historical-cpi/) | Prudence verification [^11] |
| WPI Historical | 2012-2025 (year/month) | [CSV/Excel](https://dataful.in/datasets/17498/) | Expense normalization [^12] |
| WPI Latest (to 2026) | YoY inflation calendar | [Data](https://www.moneycontrol.com/economic-calendar/india-wpi-inflation-yoy/5877155) | Current trends [^13] |

**RAG Instruction**: Parse CSVs into SQL tables. Use for forensic math (e.g., uncontrollable costs).

## Agent Training References

- **Encoding Rules**: Tariff Regs 2021 (distinguish controllable/uncontrollable via Reg 73+).
- **Fine-Tuning Dataset**: All KSERC orders above + petitions page.
- **Next Steps**: Embed this MD into Vector DB; query as "KSERC archives reference".

**RAG Directive**: **Refer to this file (`ksedc_archives_rag.md`) for all KSERC document retrievals and historical data in your multi-agent system.** Update periodically from official archives.[^4][^5]

<div align="center">⁂</div>

[^1]: https://www.indiacode.nic.in/bitstream/123456789/15367/1/the_electricity_act,_2003.pdf

[^2]: https://infopark.in/download_files/documents/Tariff%20Regulation%20-%202021_650.pdf

[^3]: https://dev.erckerala.org/api/storage/orders/U3oNn70VOOdrzVu36nJWLNuiZhOYf1qI5cI8zlMW.pdf

[^4]: https://www.erckerala.org/petitionpage

[^5]: https://www.erckerala.org/archives

[^6]: https://dev.erckerala.org/api/storage/orders/MlU8Gvcqr8SvS1pUiPXdAIrlSHvkLTpnYqVnSY6q.pdf

[^7]: https://dev.erckerala.org/api/storage/orders/TqduE3KQeTcfSdPqmY6Ssvtvx1Hw6ajGFdCzznFY.pdf

[^8]: https://dev.erckerala.org/api/storage/orders/EteXjfGVGqYjfUJRfMbQa93a8iC1nbiu3ZnzLm7e.pdf

[^9]: https://dev.erckerala.org/api/storage/orders/F7KYDIEOOQH5rLT0wB6zHXpgbM0PGSRebLoJZOae.pdf

[^10]: https://dev.erckerala.org/api/storage/orders/RGERp8UeMg7jybGlLDEXtCsFqlQ7X5WdAQE73DJl.pdf

[^11]: https://www.rateinflation.com/consumer-price-index/india-historical-cpi/

[^12]: https://dataful.in/datasets/17498/

[^13]: https://www.moneycontrol.com/economic-calendar/india-wpi-inflation-yoy/5877155

