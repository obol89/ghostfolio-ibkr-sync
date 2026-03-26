# ghostfolio-ibkr-sync

Sync Interactive Brokers trades and dividends to a self-hosted [Ghostfolio](https://ghostfol.io) instance.

This tool fetches your IBKR activity statements via Flex Queries, parses trades and dividends, maps ISINs to Yahoo Finance tickers, and pushes everything into Ghostfolio. It handles multiple sub-accounts, deduplicates activities, updates cash balances, syncs dividend payments (including withholding tax), and skips FX conversions and options trades.

## Why this exists

This project replaces [agusalex/ghostfolio-sync](https://github.com/AgustaRC/ghostfolio-sync), which has several issues:

- Broken multi-account support
- No proper ISIN-to-Yahoo-ticker mapping
- Does not handle options trades gracefully (crashes instead of skipping)
- Relies on the outdated `ibflex` Python library, which breaks on newer IBKR Flex Query fields
- No cash balance syncing

This script parses the IBKR XML directly, avoids fragile third-party libraries, and gives you full control over symbol mapping.

## Prerequisites

- A running self-hosted Ghostfolio instance
- An Interactive Brokers account with Flex Web Service enabled
- Docker (for containerized runs) or Python 3.10+ with `requests` and `pyyaml`

## IBKR Setup

### 1. Enable Flex Web Service

1. Log in to IBKR Client Portal or Account Management
2. Go to **Settings** - **Reporting** - **Flex Queries**
3. At the bottom of the page, find **Flex Web Service** and click **Configure**
4. Generate a new token (or note your existing one)
5. Set the expiration to **1 year** so you do not have to rotate it frequently
6. Save the token - you will need it as `IBKR_TOKEN`

### 2. Create a Flex Query

1. On the same Flex Queries page, click **Create** under **Activity Flex Query**
2. Give it a name like `Ghostfolio Sync`
3. Set the period to **Last 365 Calendar Days** (or whatever range you want)
4. Select the following sections and fields:

**Account Information:**
- ClientAccountID
- CurrencyPrimary

**Cash Report:**
- CurrencyPrimary
- EndingCash

**Trades (Execution):**
- ClientAccountID
- CurrencyPrimary
- AssetClass
- Symbol
- Description
- ISIN
- FIGI
- TradeID
- Multiplier
- DateTime
- TradeDate
- IBCommission
- IBCommissionCurrency
- Open/CloseIndicator
- Buy/Sell
- Exchange
- Quantity
- TradeMoney
- TradePrice

**Change in Dividend Accruals (Detail):**
- ClientAccountID
- CurrencyPrimary
- Symbol
- ISIN
- FIGI
- Date
- Quantity
- Fee
- GrossRate
- Code

5. Under **General Configuration**, set **Include Currency Rates** to **No**
6. Save the query

### 3. Multi-account setup

If you have multiple IBKR sub-accounts (e.g. individual and joint), you must create **one Flex Query per sub-account**. When creating each query, make sure only that specific account is selected in the account filter.

### 4. Find the Query ID

On the Flex Queries page, click the **info icon** (circle with "i") next to your query. The Query ID is displayed in the popup. You need this as `IBKR_QUERY_IDS`.

### 5. Data availability

Activity Statement data updates once daily after market close. Running the sync during market hours will only include trades from the previous day or earlier.

## Ghostfolio Setup

### 1. Get an auth token

```bash
curl -X POST http://localhost:3333/api/v1/auth/anonymous \
  -H 'Content-Type: application/json' \
  -d '{"accessToken": "YOUR_GHOSTFOLIO_ACCESS_TOKEN"}'
```

The response contains an `authToken` field. Use this as `GHOST_TOKEN`. Note that this token expires, so you may need to regenerate it periodically. For long-running setups, consider using a security token that does not expire.

### 2. Create an IBKR Platform

1. Go to Ghostfolio **Admin** - **Platform**
2. Click **Add Platform**
3. Enter a name like `Interactive Brokers` and a URL like `https://www.interactivebrokers.com`
4. Save it

To find the Platform ID, query the API:

```bash
curl http://localhost:3333/api/v1/platform \
  -H 'Authorization: Bearer YOUR_AUTH_TOKEN'
```

Look for the `id` field of the IBKR platform entry. Use this as `GHOST_PLATFORM_ID`.

### 3. Create accounts

Create one Ghostfolio account per IBKR sub-account:

1. Go to **Accounts** and click **Add Account**
2. Set the name to match what you will use in `GHOST_ACCOUNT_NAMES` (e.g. `IBKR Individual`, `IBKR Joint`)
3. Select the IBKR platform you created
4. Set the currency to match the sub-account base currency
5. Repeat for each sub-account

### 4. Add currencies

If your IBKR trades involve currencies that are not yet in Ghostfolio:

1. Go to **Admin** - **Market Data**
2. Search for and add any missing currency pairs (e.g. `USDEUR`, `USDGBP`)
3. Ghostfolio needs these to convert values to your base currency

### 5. After importing

After your first import, go to **Admin** and click **Gather All Data**. This fetches historical prices from Yahoo Finance for all newly imported symbols. You may need to run this multiple times if you have many new symbols.

## Configuration

All configuration is done via environment variables:

| Variable | Required | Description | Example |
|---|---|---|---|
| `IBKR_TOKEN` | Yes | IBKR Flex Web Service token | `1234567890abcdef` |
| `IBKR_ACCOUNT_IDS` | Yes | Comma-separated IBKR account IDs | `U1234567` or `U1234567,U7654321` |
| `IBKR_QUERY_IDS` | Yes | Comma-separated Flex Query IDs (one per account) | `123456` or `123456,654321` |
| `GHOST_TOKEN` | Yes | Ghostfolio auth bearer token | `eyJhbGciOi...` |
| `GHOST_HOST` | Yes | Ghostfolio base URL | `http://localhost:3333` |
| `GHOST_CURRENCY` | No | Default currency (default: `USD`) | `EUR` |
| `GHOST_PLATFORM_ID` | No | Platform ID for IBKR in Ghostfolio | `abc123-def456` |
| `GHOST_ACCOUNT_NAMES` | No | Comma-separated Ghostfolio account names (must match account count) | `IBKR Individual,IBKR Joint` |
| `MAPPING_FILE` | No | Path to symbol mapping YAML (default: `mapping.yaml`) | `/app/mapping.yaml` |
| `CRON` | No | Cron schedule for recurring runs (Docker only) | `0 6 * * *` |

## Mapping File

The mapping file is a YAML file that maps ISINs to Yahoo Finance ticker symbols. This is necessary because IBKR uses ISINs while Ghostfolio relies on Yahoo Finance for market data.

### Format

```yaml
symbol_mapping:
  US78462F1030: SPY        # SPDR S&P 500 ETF Trust
  IE00B4L5Y983: IWDA.AS    # iShares Core MSCI World
  DE0002635307: EXSA.DE    # iShares STOXX Europe 600
  US0378331005: AAPL        # Apple Inc
  IE00BKM4GZ66: EMIM.AS    # iShares Core MSCI EM IMI
```

### How to look up Yahoo Finance tickers

1. Go to [finance.yahoo.com](https://finance.yahoo.com)
2. Search for the security by name, ISIN, or IBKR symbol
3. Use the ticker shown on the Yahoo Finance page
4. For European ETFs, make sure to use the correct exchange suffix (e.g. `.AS` for Amsterdam, `.DE` for Frankfurt, `.L` for London)

### Unmapped ISINs

When the script encounters an ISIN not in the mapping file, it falls back to using the IBKR symbol. At the end of each run, it prints a summary of all unmapped ISINs in a format you can copy-paste directly into your mapping file:

```
Unmapped ISINs found. Add to your mapping file under symbol_mapping:

  US78462F1030: ???  # IBKR symbol: SPY, description: SPDR S&P 500 ETF TRUST
  DE0002635307: ???  # IBKR symbol: EXSA, description: ISHARES STOXX EU 600
```

Replace `???` with the correct Yahoo Finance ticker and add the lines to your mapping file.

## Running

### Single account

```bash
docker run --rm \
  -e IBKR_TOKEN=your_token \
  -e IBKR_ACCOUNT_IDS=U1234567 \
  -e IBKR_QUERY_IDS=123456 \
  -e GHOST_TOKEN=your_ghost_token \
  -e GHOST_HOST=http://ghostfolio:3333 \
  -e GHOST_ACCOUNT_NAMES="IBKR Main" \
  -v ./mapping.yaml:/app/mapping.yaml \
  ghostfolio-ibkr-sync
```

### Multiple accounts

```bash
docker run --rm \
  -e IBKR_TOKEN=your_token \
  -e IBKR_ACCOUNT_IDS=U1234567,U7654321 \
  -e IBKR_QUERY_IDS=123456,654321 \
  -e GHOST_TOKEN=your_ghost_token \
  -e GHOST_HOST=http://ghostfolio:3333 \
  -e GHOST_ACCOUNT_NAMES="IBKR Individual,IBKR Joint" \
  -v ./mapping.yaml:/app/mapping.yaml \
  ghostfolio-ibkr-sync
```

### Without Docker

```bash
pip install -r requirements.txt
export IBKR_TOKEN=your_token
export IBKR_ACCOUNT_IDS=U1234567
export IBKR_QUERY_IDS=123456
export GHOST_TOKEN=your_ghost_token
export GHOST_HOST=http://localhost:3333
export GHOST_ACCOUNT_NAMES="IBKR Main"
python ibkr_to_ghostfolio.py
```

## Docker Compose / Portainer

For scheduled runs, use the `CRON` environment variable. The container uses [supercronic](https://github.com/aptible/supercronic) to run the script on a cron schedule.

```yaml
services:
  ibkr-sync:
    build: .
    container_name: ghostfolio-ibkr-sync
    restart: unless-stopped
    environment:
      IBKR_TOKEN: your_token
      IBKR_ACCOUNT_IDS: U1234567,U7654321
      IBKR_QUERY_IDS: 123456,654321
      GHOST_TOKEN: your_ghost_token
      GHOST_HOST: http://ghostfolio:3333
      GHOST_ACCOUNT_NAMES: "IBKR Individual,IBKR Joint"
      MAPPING_FILE: /app/mapping.yaml
      CRON: "0 6 * * *"  # Run daily at 6 AM
    volumes:
      - ./mapping.yaml:/app/mapping.yaml
    networks:
      - ghostfolio

networks:
  ghostfolio:
    external: true
```

In Portainer, you can paste this as a stack definition and deploy it directly. Make sure the `ghostfolio` network matches the network your Ghostfolio instance is on.

## Troubleshooting

### ISIN mapping failures

If trades show up with wrong tickers or fail to import, check your `mapping.yaml`. The unmapped ISIN summary at the end of each run tells you exactly which ISINs need entries. Use Yahoo Finance to look up the correct ticker.

### Missing exchange rates

If Ghostfolio shows incorrect values or missing data, you likely need to add currency pairs. Go to **Admin** - **Market Data** and add the relevant pairs (e.g. `USDEUR`). Then run **Gather All Data**.

### Token expiry

The IBKR Flex Web Service token expires based on the expiry you set when generating it. If the script starts failing with authentication errors, generate a new token in IBKR Account Management.

The Ghostfolio auth token also expires. Regenerate it using the curl command in the Ghostfolio Setup section.

### Options trades being skipped

This is intentional. Options (assetCategory `OPT`) are skipped because Ghostfolio does not support options as an asset class. The script logs when it skips these trades.

### FX conversions being skipped

Trades with assetCategory `CASH` are FX conversions, not actual investment trades. These are skipped intentionally.

### Values not matching between IBKR and Ghostfolio

1. Run **Gather All Data** in Ghostfolio Admin to fetch latest prices
2. Check that all required currency pairs are added in Admin - Market Data
3. Verify that your mapping file has the correct Yahoo Finance tickers (some European securities have multiple listings with different prices)
4. Note that Ghostfolio uses end-of-day prices from Yahoo Finance, which may differ slightly from IBKR execution prices

### Flex Query returns no data

- Make sure you selected the correct date range in the Flex Query configuration
- Activity Statement data updates once daily after market close
- If you just opened a new account, there may be no trade history yet

## Limitations

- **No options support** - Ghostfolio does not support options as an asset class, so options trades are skipped entirely
- **Yahoo Finance data quality** - Ghostfolio relies on Yahoo Finance for price data, which can have gaps, delays, or incorrect data for some securities (especially smaller or non-US listings)
- **Daily data only** - IBKR Flex Query Activity Statements update once daily after market close, so this tool cannot sync intraday trades in real time
- **Token management** - Both the IBKR and Ghostfolio tokens expire and need manual renewal
