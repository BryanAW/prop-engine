# 🏀 Prop Engine

**A transparent, data-driven NBA player prop analysis engine**

Prop Engine is a standalone service that computes hit probabilities and expected value (EV) for NBA player props using transparent statistical methods. Built for bettors who want to understand *why* a pick is smart, not just get a recommendation.

---

## What It Does

Analyzes NBA player props (Points, Rebounds, Assists, 3-Pointers) and returns:

- **Hit Probability** — P(player goes OVER the line)
- **Expected Value** — Edge per dollar wagered
- **Projection** — Statistical forecast for the stat
- **Drivers** — Top 3 reasons behind the recommendation (e.g., "Recent form +3.4 PTS", "Opponent allows +1.8")

### Example Output

```json
{
  "market": "pts",
  "line": 27.5,
  "projection": 28.9,
  "probabilityOver": 0.61,
  "evPerUnit": 0.16,
  "drivers": [
    "Recent PTS +3.4 vs 10-game avg",
    "Opponent allows +1.8 PTS to forwards",
    "Home boost +2.0 PTS"
  ]
}
```

**Translation:** LeBron is projected at 28.9 points with a 61% chance of going over 27.5, giving you a 16% edge.

---

## How It Works

### Phase 0: Transparent Baseline (Current)

No machine learning. Pure statistical features:

1. **Recent Form** — Rolling 5/10-game averages + standard deviation
2. **Opponent Defense** — How much the opponent allows vs league average
3. **Game Context** — Home/away, rest days, back-to-backs, spread, total
4. **Injury Impact** — Adjusts minutes/usage when teammates are out
5. **Head-to-Head** — Last 4 games vs this opponent (lightly weighted)

These combine into a **Normal distribution projection**, giving us P(over line) and EV.

#### v1: NoStake PRA Model (Python)

A foundational **Points + Rebounds + Assists (PRA) projection model** implemented in pure Python (no external ML libraries). Core formula:

```
μ = B × F_match × F_min × F_usage
```

Where:
- **B** = Blended baseline PRA (60% season avg + 40% last-5 avg)
- **F_match** = Matchup factor (defense tier ± pace tier)
- **F_min** = Minutes factor (projected minutes vs season avg)
- **F_usage** = Usage factor (adjusted for key injuries)

Assumes PRA ~ Normal(μ, σ²) to convert a line into P(over) and P(under).

**Testing & Usage:**
- 44 unit tests covering all components (baseline, matchup, minutes, usage, full pipeline, probabilities)
- Interactive CLI (`python3 cli.py`) for quick evaluations
- Command-line mode for batch processing
- All math preserved; weights tunable in `NoStakePRAConfig`

### Future Phases

- **Phase 1:** Add lightweight supervised ML (Logistic Regression / XGBoost) while keeping explanations
- **Phase 2:** Blowout risk & minutes volatility modules
- **Phase 3:** Ensemble models + LLM-powered natural language explanations

---

## Features

✅ **Transparent** — See exactly why a prop is recommended  
✅ **Fast** — <100ms response time per prop  
✅ **Explainable** — No black-box predictions  
✅ **RESTful API** — Easy integration with web apps or scripts  
✅ **Type-safe** — Built in TypeScript with strict types  
✅ **Well-tested** — Unit tests for all math and feature logic  

---

## API Endpoints

### Get Prop Suggestions

```bash
GET /v1/suggest/props?gameId=12345&playerId=237&markets=pts,reb,ast
```

Returns suggestions for the specified player/markets.

### Batch Analysis

```bash
POST /v1/suggest/batch
Content-Type: application/json

{
  "requests": [
    { "gameId": "12345", "playerId": "237", "market": "pts", "line": 27.5 }
  ]
}
```

Analyze multiple props in one request.

### Available Markets

```bash
GET /v1/markets
```

Lists supported stat types and feature descriptions.

### Health Check

```bash
GET /health
```

---

## Installation

### Prerequisites

- Node.js 20+
- npm or yarn

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/prop-engine.git
cd prop-engine

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional for Phase 0)

# Run in development mode
npm run dev

# Build for production
npm run build
npm start
```

### Environment Variables

```bash
# Optional in Phase 0 (uses fixtures)
API_BASKETBALL_KEY=your_key_here
ODDS_API_KEY=your_key_here

# Server config
PORT=3000
NODE_ENV=development
LOG_LEVEL=info
```

---

## Usage Examples

### cURL

```bash
# Get suggestions for a specific player
curl "http://localhost:3000/v1/suggest/props?gameId=12345&playerId=237&markets=pts"

# Check available markets
curl "http://localhost:3000/v1/markets"
```

### JavaScript/TypeScript

```typescript
const response = await fetch(
  'http://localhost:3000/v1/suggest/props?gameId=12345&playerId=237&markets=pts,reb'
);
const data = await response.json();

console.log(`Projection: ${data.suggestions[0].projection}`);
console.log(`Hit probability: ${data.suggestions[0].probabilityOver}`);
console.log(`EV: ${data.suggestions[0].evPerUnit}`);
```

### Python (PRA Model)

**Interactive CLI:**

```bash
cd python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run interactive mode
python3 cli.py

# Or use command-line arguments for batch processing
python3 cli.py --spa 35.0 --rpa5 36.0 --min-season 35.0 --min-recent5 35.5 \
                --sigma 6.5 --line 35.5 --t-def 0 --t-pace 0
```

**Direct import:**

```python
from nostake_pra_model import evaluate_pra_prop, NoStakePRAConfig

result = evaluate_pra_prop(
    line=35.5,
    spa=39.7,
    rpa5=37.5,
    min_season=35.5,
    min_recent5=36.2,
    sigma=6.5,
    t_def=-1,  # elite defense
    t_pace=1,  # fast pace
    key_scorer_out=False,
    opp_key_defender_out=False,
)

print(f"Projected PRA: {result['mu']:.2f}")
print(f"P(OVER {35.5}): {result['p_over']:.1%}")
print(f"P(UNDER {35.5}): {result['p_under']:.1%}")
print(f"Z-score: {result['z']:.3f}")
```

---

## Project Structure

```
prop-engine/
├── src/                         # TypeScript server (Phase 1+)
│   ├── api/v1/                  # REST endpoints
│   ├── features/                # Rolling stats, opponent, context, injuries, H2H
│   ├── models/                  # Probability, EV, and ML modules
│   ├── pipeline/                # Feature assembly and scoring
│   ├── providers/               # External data sources
│   ├── types/                   # TypeScript interfaces
│   └── utils/                   # Math, time, logging helpers
├── python/                      # Python statistical models (v1+)
│   ├── nostake_pra_model.py     # Core PRA projection + probability module
│   ├── cli.py                   # Interactive & CLI entry point
│   ├── test_nostake_pra_model.py # 44 comprehensive unit tests
│   ├── requirements.txt          # Python dependencies
│   └── venv/                    # Virtual environment (ignored)
├── tests/                       # TypeScript unit and integration tests
├── scripts/                     # Data seeding and utilities
└── PROJECT_CONTEXT.md           # Detailed technical specs
```

---

## Development

### TypeScript (Server)

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run type-check
```

### Python (Statistical Models)

```bash
cd python

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run all tests
python3 -m pytest test_nostake_pra_model.py -v

# Run specific test class
python3 -m pytest test_nostake_pra_model.py::TestFullProjection -v

# Interactive CLI
python3 cli.py
```

---

## Roadmap

### Phase 0 (Current) — Transparent Baseline

#### v0.1.0 (In Progress)
- [x] Project setup
- [x] **v1: NoStake PRA Model** (Python)
  - [x] Core projection formula (baseline × matchup × minutes × usage)
  - [x] Probability conversion (Normal CDF)
  - [x] 44 comprehensive unit tests
  - [x] Interactive CLI + command-line interface
  - [x] Configurable weights
- [ ] Core feature calculators (rolling, opponent, context, injuries, H2H)
- [ ] REST API with fixtures
- [ ] Full TypeScript implementation
- [ ] Documentation & examples

### Phase 1 — Lightweight ML
- [ ] Integrate PRA model into REST API
- [ ] Logistic Regression per market (wrapping statistical models)
- [ ] Time-series validation
- [ ] Calibration (Platt/Isotonic)
- [ ] Model inference wrapper

### Phase 2 — Risk Modules
- [ ] Blowout probability model
- [ ] Minutes volatility adjustments
- [ ] Extended models (Rebounds, Assists, 3-Pointers)

### Phase 3 — Ensemble + Explainability
- [ ] Weighted ensemble (statistical + ML)
- [ ] Natural language explanations
- [ ] Real-time prop odds integration

---

## Data Sources

### Phase 0 (MVP)
- **API-Basketball** (via RapidAPI) — Player stats, box scores
- **The Odds API** — Team odds (spread, total)
- **House Lines** — Synthetic player prop lines for testing

### Future
- Add real-time prop odds feed (PrizePicks, DraftKings, etc.)
- Historical database for backtesting

---

## Math & Methodology

### Probability Calculation

Assumes player stats follow a **Normal distribution**:

```
P(X > line) = 1 - Φ((line - μ) / σ)
```

Where:
- `μ` = projection (from weighted features)
- `σ` = standard deviation (from rolling window)
- `Φ` = cumulative distribution function

### Expected Value

```
EV = p × (decimal_odds - 1) - (1 - p)
```

Where:
- `p` = P(hit)
- `decimal_odds` = converted from American odds

**Example:** 61% hit probability at -110 odds (1.91 decimal) → EV = 0.61 × 0.91 - 0.39 = 0.16 (+16% edge)

### Feature Weights

Default weights for Phase 0:
- Recent form (10-game rolling): **40%**
- Opponent defense: **15%**
- Game context (home/away, rest, spread): **25%**
- Injury adjustments: **15%**
- Head-to-head: **5%**

---

## Contributing

This is a learning project. Contributions welcome!

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards

- TypeScript with strict mode
- ESLint + Prettier enforced
- Unit tests required for new features
- Keep files under 300 lines
- Document complex math/logic

---

## License

MIT License - see LICENSE file for details

---

## FAQ

### Why not just use ML from the start?

Explainability matters. Statistical models let users understand *why* a recommendation was made. ML comes later as an enhancement, not a replacement.

### What's the accuracy?

Phase 0 targets 52-55% hit rate (better than implied odds). Phase 1 aims for 55-58% with calibrated probabilities.

### Can I use this for real betting?

This is an **educational project**. Always verify with multiple sources and bet responsibly.

### How do I get API keys?

- **API-Basketball**: Sign up at [RapidAPI](https://rapidapi.com/api-sports/api/api-basketball/) (free tier: 100 req/day)
- **The Odds API**: Register at [theoddsapi.com](https://the-odds-api.com/) (free tier: 500 req/month)

### Why TypeScript + Node instead of Python?

Faster API response times, better async handling, easier deployment to serverless platforms. Python used for ML training (Phase 1+).

---

## Contact

Part of the **NoStake Analytics** project — building tools for smarter sports betting.

Questions? Open an issue or reach out.

---

**Status:** 🚧 Phase 0.1.0 — v1 PRA Model (Testing)  
**Version:** 0.1.0-alpha  
**Last updated:** November 2025
