# finbot

A comprehensive investment analysis bot for Indian stocks that combines fundamental analysis, technical indicators, news sentiment, and sector macro trends to provide long-term investment recommendations.

## Features

- **Fundamental Analysis**: Analyzes financial ratios, growth metrics, and valuation indicators
- **Technical Analysis**: Evaluates price trends, momentum, and support/resistance levels
- **News Sentiment**: Processes recent news and social media sentiment
- **Sector Macro Analysis**: Considers sector-specific trends and macroeconomic factors
- **Alternative Investments**: Suggests comparable investment opportunities
- **Risk-Adjusted Recommendations**: Provides position sizing and entry timing based on risk profile

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd finbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line

Run analysis for a specific company:

```bash
python main.py "Reliance" --risk medium --horizon 2.0
```

**Arguments:**
- `company`: Company name (e.g., "Reliance", "TCS", "HDFC Bank")
- `--risk`: Risk level - "low", "medium", or "high" (default: medium)
- `--horizon`: Investment horizon in years (default: 2.0)

**Examples:**
```bash
# Conservative analysis for TCS
python main.py "TCS" --risk low --horizon 3.0

# Aggressive analysis for HDFC Bank
python main.py "HDFC Bank" --risk high --horizon 1.5

# Enable verbose debug logs
python main.py "Reliance" --risk medium --horizon 2.0 --log-level debug
```

### VSCode Debugging

1. Open the project in VSCode
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select "Debug finbot main.py" from the dropdown
4. Modify the arguments in `.vscode/launch.json` if needed
5. Press F5 to start debugging

The default debug configuration analyzes Reliance with medium risk over 2 years.

## Output

The bot provides:
- **Final Decision**: Buy/Hold/Sell recommendation with confidence score
- **Entry Timing**: When to enter the position
- **Position Size**: Recommended allocation based on risk profile
- **Rationale**: Detailed explanation of the decision
- **News Summary**: Recent news sentiment analysis

### Run artifacts

Each execution saves all intermediate and final results under `runs/<timestamp>_<company>/`:
- `ticker.json`
- `fundamentals.json`
- `technical.json`
- `news.json`
- `sector_macro.json`
- `alternatives.json`
- `decision.json`
- `bundle.json` (aggregated final result)

## Architecture

The application uses a graph-based orchestration pattern:

- **Advisors**: Specialized analysis modules (fundamentals, technical, news, etc.)
- **Orchestrator**: Coordinates data flow between advisors
- **Schemas**: Type-safe data structures for analysis results
- **Tools**: Data fetching and processing utilities

## Configuration

Key configuration options in `config.py`:
- API endpoints and keys
- Analysis parameters
- Logging settings

## Development

### Project Structure
```
finbot/
├── advisors/          # Analysis modules
├── tools/            # Data fetching utilities
├── main.py           # Entry point
├── orchestrator.py   # Workflow coordination
├── schemas.py        # Data models
└── config.py         # Configuration
```

### Adding New Analysis

1. Create a new advisor in `advisors/`
2. Add corresponding schema in `schemas.py`
3. Update the orchestrator workflow in `orchestrator.py`

## License

[Add your license information here]