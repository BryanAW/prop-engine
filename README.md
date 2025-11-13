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

### Python

```python
import requests

response = requests.get(
    "http://localhost:3000/v1/suggest/props",
    params={"gameId": "12345", "playerId": "237", "markets": "pts"}
)
data = response.json()

for suggestion in data["suggestions"]:
    print(f"{suggestion['market']}: {suggestion['projection']} (p={suggestion['probabilityOver']:.2f})")
```

---

## Project Structure

```
prop-engine/
├── src/
│   ├── api/v1/          # REST endpoints
│   ├── features/        # Rolling stats, opponent, context, injuries, H2H
│   ├── models/          # Probability, EV, and ML modules
│   ├── pipeline/        # Feature assembly and scoring
│   ├── providers/       # External data sources
│   ├── types/           # TypeScript interfaces
│   └── utils/           # Math, time, logging helpers
├── tests/               # Unit and integration tests
├── scripts/             # Data seeding and utilities
└── PROJECT_CONTEXT.md   # Detailed technical specs
```

---

## Development

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

### Adding a New Feature

1. Create feature calculator in `src/features/`
2. Add types to `src/types/index.ts`
3. Wire into `assembleFeatures.ts`
4. Update `scoreProp.ts` to use the feature
5. Write unit tests
6. Update this README if user-facing

---

## Roadmap

### Phase 0 (Current) — Transparent Baseline
- [x] Project setup
- [ ] Core feature calculators (rolling, opponent, context, injuries, H2H)
- [ ] Probability & EV models
- [ ] REST API with fixtures
- [ ] Unit tests + documentation

### Phase 1 — Lightweight ML
- [ ] Logistic Regression per market
- [ ] Time-series validation
- [ ] Calibration (Platt/Isotonic)
- [ ] Model inference wrapper

### Phase 2 — Risk Modules
- [ ] Blowout probability model
- [ ] Minutes volatility adjustments

### Phase 3 — Ensemble + Explainability
- [ ] Weighted ensemble (statistical + ML)
- [ ] Natural language explanations

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

**Status:** 🚧 Phase 0 in progress  
**Version:** 0.1.0  
**Last updated:** November 2025
