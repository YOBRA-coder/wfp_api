"""
Education content — the Learning Hub's course/lesson data.

Kept separate from database.py so the actual curriculum is easy to read, edit,
and extend without wading through SQL. Bump CONTENT_VERSION whenever COURSES
changes meaningfully; database.py reseeds education_courses (and resets
progress) whenever the stored version is behind this one.

Lesson shape (all fields respected by the Education.jsx viewer):
  title:    str
  summary:  str                       — one-line "what you'll learn", shown under the title
  duration: int                       — minutes, shown in the lesson list
  sections: [ {heading, body}, ... ]  — the lesson body, broken into real sub-topics
  notes:    [ str, ... ]              — "Key Takeaways" cheat-sheet shown at the end
  quiz:     [ {q, options, answer, explanation}, ... ] — 2-4 questions per lesson,
            each graded individually with its own explanation (not just one Q per lesson)
"""

CONTENT_VERSION = 2

COURSES = [
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Forex Fundamentals",
        "description": "A complete beginner's foundation — how the market works, how trades are priced, and how to read a quote correctly before you risk a cent.",
        "category": "basics", "level": "beginner",
        "lessons": [
            {
                "title": "What Is the Forex Market?",
                "summary": "How the world's largest financial market actually works, and who's really trading against you.",
                "duration": 8,
                "sections": [
                    {"heading": "A market with no single exchange", "body": "Forex (foreign exchange) is the market where currencies are exchanged for one another. Unlike stocks, there's no central exchange like the NYSE — trading happens over-the-counter through a global network of banks, brokers, and electronic platforms. Roughly $7.5 trillion changes hands every single day, more than every stock market on Earth combined."},
                    {"heading": "Who actually moves the market", "body": "Central banks (setting interest rates and defending currencies), commercial banks (trading for clients and themselves), hedge funds and institutional traders, multinational corporations (hedging revenue in foreign currencies), and retail traders like you — in that rough order of size. Retail volume is a small slice of the total; understanding that keeps expectations realistic."},
                    {"heading": "Why it never fully closes", "body": "Because trading passes between financial centers as the Earth rotates — Sydney, then Tokyo, then London, then New York — the market is open 24 hours a day, five days a week. It closes for the weekend because most of that institutional volume simply isn't at their desks; liquidity doesn't disappear so much as go quiet."},
                ],
                "notes": [
                    "Forex has no central exchange — it's a decentralized, over-the-counter network.",
                    "Daily volume (~$7.5T) dwarfs every stock market combined.",
                    "Central banks and institutions drive the bulk of volume, not retail traders.",
                    "The market runs 24/5, following financial centers around the globe.",
                ],
                "quiz": [
                    {"q": "Forex trading happens through:", "options": ["A single central exchange, like the NYSE", "A decentralized network of banks and brokers", "Only government-run trading desks"], "answer": 1, "explanation": "There's no forex equivalent of the NYSE floor — it's entirely over-the-counter, routed through banks, brokers, and electronic platforms worldwide."},
                    {"q": "Why is the forex market open 24 hours during the week?", "options": ["Regulators require it", "Trading passes between global financial centers as the day progresses", "Retail traders demanded it"], "answer": 1, "explanation": "As Sydney closes, Tokyo is opening; as Tokyo winds down, London opens; then New York — creating a continuous chain of active sessions."},
                    {"q": "Roughly how much daily volume does forex do compared to global stock markets?", "options": ["About the same", "Far less", "More than all of them combined"], "answer": 2, "explanation": "At ~$7.5 trillion/day, forex volume exceeds the combined daily turnover of every stock exchange in the world."},
                ],
            },
            {
                "title": "Reading a Currency Pair & Quote",
                "summary": "Base vs quote currency, bid/ask, and what actually happens when you click Buy or Sell.",
                "duration": 7,
                "sections": [
                    {"heading": "Base and quote currency", "body": "Every pair is written BASE/QUOTE — e.g. EUR/USD. The quote tells you how much of the quote currency it takes to buy one unit of the base. EUR/USD = 1.0850 means 1 euro buys 1.0850 US dollars. When you BUY EUR/USD, you're buying euros and simultaneously selling dollars; you profit if the euro strengthens against the dollar."},
                    {"heading": "Bid, ask, and the spread", "body": "Every quote actually has two prices: the BID (what you get if you sell right now) and the ASK (what you pay if you buy right now). The ASK is always slightly higher — that gap is the SPREAD, and it's effectively the broker's built-in transaction cost. On EUR/USD a typical spread might be 0.6–1.2 pips; on more exotic pairs it can be far wider."},
                    {"heading": "Majors, minors, and exotics", "body": "Major pairs all include USD paired with a large economy's currency (EUR/USD, GBP/USD, USD/JPY) and have the tightest spreads and deepest liquidity. Minor pairs (crosses) exclude USD (EUR/GBP, GBP/JPY). Exotic pairs pair a major currency with an emerging-market one (USD/TRY, USD/ZAR) — wider spreads, more volatility, more risk."},
                ],
                "notes": [
                    "BASE/QUOTE — the number tells you how much quote currency buys one unit of base.",
                    "Buying EUR/USD = buying EUR, selling USD in the same trade.",
                    "The spread (ask − bid) is the broker's built-in cost of every trade.",
                    "Majors have the tightest spreads; exotics have the widest and most risk.",
                ],
                "quiz": [
                    {"q": "In EUR/USD, which currency is the 'base'?", "options": ["USD", "EUR", "Neither — they're equal"], "answer": 1, "explanation": "The base currency is always listed first. In EUR/USD, EUR is the base and USD is the quote."},
                    {"q": "If EUR/USD = 1.0850 and you BUY, you profit when:", "options": ["EUR weakens vs USD", "EUR strengthens vs USD", "Both stay flat"], "answer": 1, "explanation": "Buying EUR/USD means you're long the base currency (EUR) — you profit as it strengthens against the quote currency (USD)."},
                    {"q": "The spread is:", "options": ["A monthly account fee", "The gap between bid and ask, the broker's built-in cost per trade", "A tax on profits"], "answer": 1, "explanation": "The spread is paid on every single trade the moment you open it — it's the difference between the price you buy at and the price you could immediately sell at."},
                ],
            },
            {
                "title": "Pips, Points, and Price Precision",
                "summary": "How price movement is actually measured — and why JPY pairs are the exception every beginner trips over.",
                "duration": 7,
                "sections": [
                    {"heading": "What a pip is", "body": "A pip (\"percentage in point\") is the standard unit for measuring price movement. For most pairs it's the 4th decimal place: EUR/USD moving from 1.0850 to 1.0860 is a 10-pip move. Many brokers quote a 5th decimal (a 'pipette', 1/10th of a pip) for extra precision, but the pip itself stays the 4th decimal."},
                    {"heading": "The JPY exception", "body": "Yen pairs are quoted with only 2 decimal places, because the yen has much lower per-unit value. USD/JPY at 150.00 moving to 150.10 is a 10-pip move — the pip is the 2nd decimal place, not the 4th. This trips up almost every beginner at least once; it's worth deliberately memorizing."},
                    {"heading": "Why pip precision matters for risk", "body": "Every risk calculation — position size, stop-loss distance, potential loss — is built on pips. Miscounting them (especially on JPY pairs) is one of the most common beginner errors, and it directly means placing the wrong size trade. Always double-check which decimal place is 'the pip' for the specific pair you're trading."},
                ],
                "notes": [
                    "1 pip = 4th decimal place for most pairs, 2nd decimal for JPY pairs.",
                    "A 'pipette' is 1/10th of a pip — extra precision, not a different unit.",
                    "Miscounting pips on JPY pairs is one of the most common beginner mistakes.",
                    "Pip math underlies every position-size and risk calculation you'll ever do.",
                ],
                "quiz": [
                    {"q": "EUR/USD moves from 1.0850 to 1.0920. How many pips?", "options": ["7 pips", "70 pips", "0.7 pips"], "answer": 1, "explanation": "1.0920 − 1.0850 = 0.0070, and since 1 pip = 0.0001 for EUR/USD, that's 70 pips."},
                    {"q": "USD/JPY moves from 149.50 to 149.80. How many pips?", "options": ["3 pips", "30 pips", "300 pips"], "answer": 1, "explanation": "For JPY pairs, 1 pip = 0.01. 149.80 − 149.50 = 0.30, which is 30 pips."},
                    {"q": "Why does pip precision matter so much?", "options": ["It doesn't, it's cosmetic", "Every position-size and risk calculation depends on it", "Only brokers care about it"], "answer": 1, "explanation": "Getting pips wrong means your stop-loss distance and lot size calculations are wrong too — directly affecting how much you actually risk."},
                ],
            },
            {
                "title": "Lot Sizes, Leverage & Margin",
                "summary": "Standard vs mini vs micro lots, what leverage actually does to your risk, and how margin calls happen.",
                "duration": 9,
                "sections": [
                    {"heading": "Lot sizes", "body": "A standard lot = 100,000 units of the base currency. A mini lot = 10,000. A micro lot = 1,000. A nano lot (not all brokers offer it) = 100. On a 0.01-lot (micro) EUR/USD trade, 1 pip is worth roughly $0.10; on a 1.0-lot (standard) trade, 1 pip is worth roughly $10. Position size is the single biggest lever you control over how much a trade can hurt or help you."},
                    {"heading": "Leverage — the double-edged tool", "body": "Leverage lets you control a large position with a small deposit. 1:100 leverage means $100 of your own money can control a $10,000 position. This magnifies both gains AND losses proportionally — leverage doesn't make a strategy more profitable, it just makes the SAME percentage move worth more money in both directions."},
                    {"heading": "Margin and margin calls", "body": "Margin is the deposit your broker holds aside from your balance to keep a leveraged position open. If losses eat into your account enough that your equity falls below the required margin, you get a margin call (a warning) and eventually a stop-out (forced position closure) to protect the broker from your account going negative. Overleveraging — using far more leverage than your risk plan calls for — is the #1 way beginner accounts get wiped out fast."},
                ],
                "notes": [
                    "Standard = 100,000 units, mini = 10,000, micro = 1,000, nano = 100.",
                    "On 0.01 lot EUR/USD, ~$0.10/pip; on 1.0 lot, ~$10/pip.",
                    "Leverage amplifies both wins AND losses — it never improves your edge.",
                    "A margin call means your account is running out of room; a stop-out force-closes positions.",
                    "Overleveraging (not the market) is the #1 cause of fast beginner account blowups.",
                ],
                "quiz": [
                    {"q": "On a 0.01-lot EUR/USD trade, roughly how much is 20 pips worth?", "options": ["$2", "$20", "$200"], "answer": 0, "explanation": "At roughly $0.10/pip on a 0.01 lot, 20 pips ≈ $2."},
                    {"q": "1:100 leverage means:", "options": ["You can only lose 1% of your account", "$100 of your capital can control a $10,000 position", "Your broker guarantees 100% returns"], "answer": 1, "explanation": "Leverage is a capital multiplier for position size — it says nothing about guaranteed returns, and it magnifies losses exactly as much as gains."},
                    {"q": "What most commonly wipes out beginner accounts quickly?", "options": ["Bad luck in the market", "Overleveraging relative to their risk plan", "Trading too few pairs"], "answer": 1, "explanation": "Using far more leverage/position size than a sound risk plan allows means normal, ordinary market moves can produce outsized account damage."},
                ],
            },
            {
                "title": "Market Sessions & When to Trade",
                "summary": "Sydney, Tokyo, London, New York — when volume and volatility actually show up, and when to sit on your hands.",
                "duration": 6,
                "sections": [
                    {"heading": "The four sessions", "body": "Sydney (22:00–07:00 UTC), Tokyo (00:00–09:00 UTC), London (08:00–17:00 UTC), New York (13:00–22:00 UTC). Each session has a character: Tokyo tends to be range-bound and quieter on majors (though very active for JPY crosses), London is where the real directional volume often starts, and New York frequently extends or reverses the London move."},
                    {"heading": "The overlap is where it happens", "body": "The London/New York overlap (roughly 13:00–17:00 UTC) sees the highest combined volume and tightest spreads of the entire trading day — most serious intraday setups cluster here. The Sydney/Tokyo overlap is comparatively quiet, which suits range strategies but not breakout strategies."},
                    {"heading": "Matching your strategy to the session", "body": "Trading a breakout strategy during the quiet Tokyo-only hours (for a non-JPY pair) usually means false signals — there simply isn't enough volume behind the move. Conversely, trading a mean-reversion/range strategy during the London/NY overlap can get run over by genuine trending volume. Know which session you're trading in and pick a strategy that fits it."},
                ],
                "notes": [
                    "London/New York overlap (≈13:00–17:00 UTC) has the highest volume and tightest spreads.",
                    "Tokyo is comparatively quiet for majors but active for JPY crosses.",
                    "Breakout strategies want high-volume sessions; range strategies suit quieter ones.",
                    "All times are UTC — convert to your own local time before setting a trading schedule.",
                ],
                "quiz": [
                    {"q": "Which overlap typically has the highest volume?", "options": ["Sydney/Tokyo", "London/New York", "Tokyo/London"], "answer": 1, "explanation": "The London/New York overlap combines two of the largest financial centers actively trading at once, producing the day's peak liquidity."},
                    {"q": "A breakout strategy on EUR/USD is most likely to give false signals during:", "options": ["The London/NY overlap", "The quiet Tokyo-only hours", "London open"], "answer": 1, "explanation": "Breakouts need real volume behind them to hold; in low-liquidity hours, price can 'break out' and reverse right back due to thin participation."},
                ],
            },
            {
                "title": "Order Types & How Trades Get Executed",
                "summary": "Market, limit, and stop orders — and why understanding execution matters as much as understanding direction.",
                "duration": 7,
                "sections": [
                    {"heading": "Market orders", "body": "A market order fills immediately at the best available current price. Simple and fast, but during fast-moving news or thin liquidity, the actual fill can 'slip' away from the price you saw on screen — this is called slippage, and it's normal, not a broker conspiracy."},
                    {"heading": "Limit and stop orders", "body": "A limit order only fills at your specified price or better (buy limit below current price, sell limit above) — useful for entering on a pullback to a level you've identified. A stop order triggers a market order once price reaches a level (buy stop above current price, sell stop below) — useful for entering breakouts in the direction price is already moving."},
                    {"heading": "Stop-loss and take-profit as pending orders", "body": "Your stop-loss and take-profit are themselves a form of pending order attached to an open trade — SL is a stop order in the losing direction, TP is a limit order in the winning direction. Setting them at trade entry (not 'later, once I see how it goes') is what actually enforces your risk plan instead of just intending to."},
                ],
                "notes": [
                    "Market orders fill now, at the best available price — with possible slippage in fast markets.",
                    "Limit orders enter at your price or better; stop orders trigger a market order once price reaches a level.",
                    "SL is essentially a stop order, TP is essentially a limit order — both attached to your open position.",
                    "Set SL/TP at entry — deciding 'later' is how discipline quietly disappears.",
                ],
                "quiz": [
                    {"q": "A buy limit order is placed:", "options": ["Above the current price", "Below the current price", "Exactly at the current price"], "answer": 1, "explanation": "A buy limit waits for price to come down to a more favorable level before filling — it's placed below current price."},
                    {"q": "Slippage happens when:", "options": ["Your broker is cheating you", "The actual fill price differs from the displayed price, usually in fast/thin markets", "You use a limit order"], "answer": 1, "explanation": "Slippage is a normal execution phenomenon during volatile or low-liquidity moments, not evidence of broker manipulation — limit orders are actually the tool that avoids it, since they only fill at your price or better."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Technical Analysis Mastery",
        "description": "Advanced, practical chart-reading — support/resistance, momentum, volatility, and how to combine timeframes so your entries actually align with the bigger picture.",
        "category": "technical", "level": "intermediate",
        "lessons": [
            {
                "title": "Support & Resistance — Reading Market Memory",
                "summary": "Why price 'remembers' certain levels, and how to tell a strong level from a weak one.",
                "duration": 10,
                "sections": [
                    {"heading": "What S/R actually represents", "body": "Support is a price floor where buying pressure has repeatedly overwhelmed selling pressure; resistance is a ceiling where the opposite happens. These levels form because real orders cluster there — stop-losses, take-profits, and fresh entries from traders who remember the level mattering before. It's market psychology made visible on a chart."},
                    {"heading": "Strength of a level", "body": "A level tested and held multiple times is more significant than one touched once. But there's a trade-off: each additional touch also slightly weakens a level, because it's consuming the orders resting there. The strongest breaks often come after a level has been tested 3-4 times and finally gives way — the resting liquidity is exhausted."},
                    {"heading": "Role reversal — the flip", "body": "When support breaks, it very often becomes new resistance on a retest (and vice versa for broken resistance becoming support). This happens because traders who bought at the old support and are now underwater tend to sell into any bounce back up to their entry, creating fresh selling pressure exactly at the old level."},
                    {"heading": "Zones, not lines", "body": "Treat S/R as a zone, not a single precise price. Markets rarely respect a level to the exact pip — draw a small range around the level (a few pips to a few dozen, depending on timeframe) and expect reactions anywhere inside it, not exactly at your drawn line."},
                ],
                "notes": [
                    "S/R levels form because real orders cluster there — it's visible order-flow psychology.",
                    "More touches = more significant, but also slightly weaker (liquidity gets consumed).",
                    "Broken support commonly flips to resistance, and vice versa.",
                    "Treat levels as zones, not exact lines — price rarely respects a single pip precisely.",
                ],
                "quiz": [
                    {"q": "When a support level is broken, it typically becomes:", "options": ["A neutral zone with no significance", "New resistance", "An even stronger support"], "answer": 1, "explanation": "Traders who bought at the old support and are now underwater tend to sell into a retest, turning the old floor into a new ceiling."},
                    {"q": "A level touched and held 5 times vs. one touched once — which is generally more significant, and why?", "options": ["The 5-touch level, because it shows repeated buyer/seller interest", "The 1-touch level, because it's 'fresh'", "They're equally significant"], "answer": 0, "explanation": "Repeated tests show the level genuinely matters to market participants, though each test also uses up some of the resting orders there."},
                    {"q": "The best practice for drawing S/R is to:", "options": ["Draw an exact single-pip line", "Draw a zone/range around the level", "Ignore S/R entirely on lower timeframes"], "answer": 1, "explanation": "Price reacts to a general area, not one exact price — a zone captures the real behavior better than a single line."},
                ],
            },
            {
                "title": "Momentum: RSI & Stochastic",
                "summary": "Reading overbought/oversold correctly, and why divergence is one of the most reliable momentum signals.",
                "duration": 9,
                "sections": [
                    {"heading": "RSI basics", "body": "RSI (Relative Strength Index) oscillates 0-100 and measures the speed/magnitude of recent price changes. Below 30 is traditionally 'oversold', above 70 is 'overbought'. But in a strong trend, RSI can stay pinned above 70 (or below 30) for a long stretch — 'overbought' does not mean 'about to reverse,' it means momentum is strong."},
                    {"heading": "RSI divergence — the real signal", "body": "Divergence is far more actionable than the raw level: if price makes a new high but RSI makes a LOWER high, that's bearish divergence — momentum is fading even as price pushes higher, often preceding a reversal or at least a pause. The mirror case (price makes a new low, RSI makes a higher low) is bullish divergence."},
                    {"heading": "Stochastic Oscillator", "body": "Stochastic compares the current close to the recent high-low range, also on a 0-100 scale, using two lines (%K and %D). It's more sensitive/faster than RSI, which makes it good for range-bound markets but noisier in strong trends. A %K/%D crossover in oversold/overbought territory is the classic signal, but it works best combined with S/R, not alone."},
                    {"heading": "Combining momentum with structure", "body": "Momentum indicators are strongest as CONFIRMATION, not standalone signals. RSI oversold at a random price is weak; RSI oversold exactly at a major support zone, with bullish divergence, is a much higher-quality setup. Always ask: what is price DOING (structure) before asking what momentum SAYS."},
                ],
                "notes": [
                    "RSI < 30 = oversold, RSI > 70 = overbought — but strong trends can stay there a long time.",
                    "Divergence (price vs. RSI direction disagreeing) is usually more reliable than the raw level.",
                    "Stochastic is faster/noisier than RSI — better suited to ranges than strong trends.",
                    "Momentum indicators work best as confirmation of a structural setup, not alone.",
                ],
                "quiz": [
                    {"q": "Price makes a new high, but RSI makes a LOWER high. This is:", "options": ["Bullish divergence", "Bearish divergence", "No signal at all"], "answer": 1, "explanation": "This mismatch — price up, momentum down — is classic bearish divergence, warning that the rally may be losing steam."},
                    {"q": "RSI sitting above 70 during a strong uptrend means:", "options": ["A reversal is guaranteed imminently", "Momentum is strong; overbought alone isn't a reversal signal", "You should always sell immediately"], "answer": 1, "explanation": "In genuine trends, momentum oscillators can stay pinned at extremes for extended periods — 'overbought' describes strength, not automatic exhaustion."},
                    {"q": "Momentum signals are generally most reliable when:", "options": ["Used completely alone, on any random price level", "Combined with a structural level like S/R", "Ignored in favor of price action only"], "answer": 1, "explanation": "An oscillator signal at a meaningless price is weak; the same signal at a major structural level is a much higher-quality confluence setup."},
                ],
            },
            {
                "title": "MACD & Trend Confirmation",
                "summary": "How MACD is built from moving averages, and reading the histogram before the crossover even happens.",
                "duration": 8,
                "sections": [
                    {"heading": "What MACD is made of", "body": "MACD = 12-period EMA minus 26-period EMA (the MACD line). A 9-period EMA of that line is the Signal line. The Histogram = MACD line minus Signal line, visualized as bars. Because it's built entirely from EMAs, MACD is fundamentally a trend/momentum tool, not a pure oscillator like RSI."},
                    {"heading": "Reading crossovers", "body": "MACD crossing above the Signal line is a bullish signal; crossing below is bearish. The further this crossover happens from the zero line, the more established the existing trend is — crossovers near zero often mark genuine trend changes, while crossovers far from zero can just be a pullback within an ongoing trend."},
                    {"heading": "The histogram — an earlier read", "body": "The histogram often shifts direction (shrinking, then growing again in the opposite lean) before the actual crossover happens — because it's the DIFFERENCE between the two lines, and that difference starts narrowing as soon as momentum shifts, even before the lines physically cross. Watching histogram shrinkage gives you an earlier (though less confirmed) read than waiting for the full crossover."},
                ],
                "notes": [
                    "MACD line = 12 EMA − 26 EMA; Signal = 9 EMA of MACD; Histogram = MACD − Signal.",
                    "MACD crossing above Signal = bullish; below = bearish.",
                    "Crossovers near the zero line often mark real trend changes; far from zero, often just pullbacks.",
                    "Histogram shrinkage/growth often leads the crossover — an earlier but less confirmed signal.",
                ],
                "quiz": [
                    {"q": "The MACD histogram is calculated as:", "options": ["MACD line + Signal line", "MACD line − Signal line", "Price − MACD line"], "answer": 1, "explanation": "The histogram visualizes the gap between the MACD line and its own signal line — shrinking toward zero as the two lines converge."},
                    {"q": "A MACD crossover happening far above the zero line most likely represents:", "options": ["A brand-new trend just starting", "A pullback/continuation within an already-established trend", "A guaranteed reversal"], "answer": 1, "explanation": "Crossovers close to the zero line are more associated with genuine trend changes; ones far from zero tend to just reflect a pause within a trend already underway."},
                    {"q": "Why does the histogram sometimes shift before the actual MACD/Signal crossover?", "options": ["It's a coincidence", "It measures the gap between the two lines, which starts narrowing as momentum shifts", "It's calculated on a different timeframe"], "answer": 1, "explanation": "Since the histogram IS the difference between MACD and Signal, it naturally starts shrinking as soon as momentum shifts direction, ahead of the lines physically crossing."},
                ],
            },
            {
                "title": "Bollinger Bands & Volatility",
                "summary": "Reading squeezes, walks, and mean-reversion signals from a volatility-based indicator.",
                "duration": 7,
                "sections": [
                    {"heading": "The three lines", "body": "Bollinger Bands consist of a middle band (typically a 20-period SMA), an upper band (+2 standard deviations), and a lower band (−2 standard deviations). Because they're based on standard deviation, the bands automatically widen in volatile conditions and narrow in quiet ones — they adapt to the market instead of using a fixed distance."},
                    {"heading": "The squeeze", "body": "When the bands compress tightly together, volatility has contracted sharply — a 'squeeze.' This doesn't tell you direction, but it's a strong signal that an expansion (often a sharp breakout move) is coming, because volatility is cyclical and tends to mean-revert from extremes in either direction."},
                    {"heading": "Band walks vs. reversals", "body": "In a genuinely strong trend, price can 'walk the band' — repeatedly touching or riding along the upper (or lower) band without reverting to the middle. This is the opposite of a simple mean-reversion read; treating every upper-band touch as an automatic sell in a strong uptrend is a common and costly mistake."},
                ],
                "notes": [
                    "Bands = 20 SMA middle, ±2 standard deviations for upper/lower — they widen/narrow with volatility.",
                    "A tight 'squeeze' signals contraction and often precedes a sharp breakout — direction unknown.",
                    "'Walking the band' in a strong trend is normal, not an automatic reversal signal.",
                    "Bollinger Bands describe volatility, not direction — pair with trend/structure reads.",
                ],
                "quiz": [
                    {"q": "A Bollinger Band squeeze most reliably signals:", "options": ["An imminent reversal to the downside specifically", "That volatility is likely to expand soon (direction unknown)", "That the pair should be avoided entirely"], "answer": 1, "explanation": "The squeeze tells you volatility has contracted and is likely to expand — it does not by itself tell you which direction the breakout will go."},
                    {"q": "Price repeatedly touching the upper band during a strong uptrend usually means:", "options": ["An automatic sell signal every time", "The trend is strong — 'walking the band' is normal in trends", "The indicator is broken"], "answer": 1, "explanation": "In strong trends, price can ride the upper band for extended periods; treating every touch as an automatic reversal signal is a common mistake."},
                ],
            },
            {
                "title": "Candlestick Patterns That Actually Matter",
                "summary": "Cutting through the giant candlestick glossary down to the handful of patterns with real statistical edge.",
                "duration": 9,
                "sections": [
                    {"heading": "Pin bars / rejection candles", "body": "A pin bar has a small body and a long wick rejecting one direction — it shows price tried to go further but was firmly pushed back. Context matters enormously: a pin bar at a random mid-range price is noise; the same pin bar at a major S/R level, aligned with the higher-timeframe trend, is a genuinely strong signal."},
                    {"heading": "Engulfing patterns", "body": "A bullish engulfing candle fully engulfs the prior candle's body (opens below the prior close, closes above the prior open) — showing a decisive shift in control from sellers to buyers within a single bar. Bearish engulfing is the mirror. Like pin bars, engulfing patterns matter far more at a structural level than in the middle of nowhere."},
                    {"heading": "Inside bars & consolidation", "body": "An inside bar's entire range sits within the previous bar's range — a pause/consolidation signal. A break of the inside bar's high or low often signals continuation of the prior move, especially in a trending market; inside bars at a major level can also mark indecision before a reversal."},
                    {"heading": "The context rule", "body": "Every candlestick pattern is a LOCAL signal — it describes what just happened in one or two bars. Its reliability depends almost entirely on where it happens: at a major S/R level, aligned with the higher-timeframe trend, it's meaningful; in the middle of a range with no context, it's close to random noise. Never trade a pattern in isolation."},
                ],
                "notes": [
                    "Pin bars show rejection; engulfing candles show a decisive shift in control.",
                    "Inside bars mark consolidation — a break of their range often signals continuation.",
                    "Context (S/R level + higher-timeframe trend) matters far more than the pattern shape itself.",
                    "No candlestick pattern should be traded in isolation from structure.",
                ],
                "quiz": [
                    {"q": "A bullish engulfing candle:", "options": ["Has a smaller body than the prior candle", "Opens below and closes above the prior candle's full body", "Only appears in downtrends"], "answer": 1, "explanation": "The defining feature is that its body fully 'engulfs' the previous candle's body, showing buyers decisively overpowering the prior session."},
                    {"q": "A pin bar's reliability depends most on:", "options": ["Its exact wick-to-body ratio down to the pixel", "Where it forms (S/R level, higher-timeframe trend alignment)", "The color chosen for the candle"], "answer": 1, "explanation": "Context is what separates a meaningful rejection candle from noise — the same shape means very different things at a major level vs. in open space."},
                    {"q": "An inside bar represents:", "options": ["A period of high volatility", "A pause/consolidation within the prior bar's range", "A guaranteed trend reversal"], "answer": 1, "explanation": "Because its full range sits inside the previous bar, it shows the market pausing to digest the prior move before its next decision."},
                ],
            },
            {
                "title": "Multi-Timeframe Analysis — Trading Top-Down",
                "summary": "The professional workflow: bias, structure, and entry each come from a different timeframe, in that order.",
                "duration": 10,
                "sections": [
                    {"heading": "The top-down workflow", "body": "Daily chart = overall bias (which direction do you even want to be looking to trade?). H4 = structure (where are the real S/R levels and the current swing pattern?). H1 = setup confirmation (is a valid pattern forming at the H4 level?). M15 = precise entry timing. Skipping straight to a lower timeframe without the higher-timeframe context is the single most common structural mistake new traders make."},
                    {"heading": "Why trading against the daily bias is costly", "body": "A perfect-looking M15 sell setup, taken while the daily chart is in a clear, strong uptrend, is fighting the dominant order flow. It can still work occasionally, but the odds are stacked against it — you're betting against the largest, most persistent group of participants in the market."},
                    {"heading": "Alignment gives confluence", "body": "The strongest setups occur when multiple timeframes agree: daily bias bullish, H4 shows price pulling back into a known support zone, H1 shows a bullish reversal candlestick pattern forming right there. Each additional aligned timeframe is another layer of confluence — not proof, but meaningfully better odds."},
                ],
                "notes": [
                    "Daily = bias, H4 = structure, H1 = setup confirmation, M15 = entry timing.",
                    "Trading against the daily/higher-timeframe bias fights the dominant order flow.",
                    "The best setups show alignment across multiple timeframes — that's confluence.",
                    "Skipping the higher-timeframe check is the most common structural beginner mistake.",
                ],
                "quiz": [
                    {"q": "Which timeframe typically sets your overall directional bias?", "options": ["M15", "H1", "Daily"], "answer": 2, "explanation": "The daily chart shows the dominant, longer-term order flow — the context every lower-timeframe decision should respect."},
                    {"q": "A great-looking M15 setup that contradicts the daily trend is:", "options": ["Always safe to take, timeframe doesn't matter", "Fighting the dominant order flow — lower-probability, not impossible", "Guaranteed to fail"], "answer": 1, "explanation": "It's not automatically doomed, but it's working against the largest, most persistent participants — the odds tilt against it."},
                    {"q": "'Confluence' refers to:", "options": ["Using only one indicator at a time", "Multiple independent signals/timeframes aligning on the same conclusion", "A specific candlestick pattern"], "answer": 1, "explanation": "Confluence means several separate pieces of evidence (timeframes, structure, momentum) all pointing the same direction — strengthening the case for a setup."},
                ],
            },
            {
                "title": "Chart Patterns: Continuation & Reversal",
                "summary": "Flags, triangles, head-and-shoulders, and double tops — what they mean and how to measure a target.",
                "duration": 9,
                "sections": [
                    {"heading": "Continuation patterns", "body": "Flags and pennants form after a sharp move as a brief pause/consolidation, typically sloping against the prior trend (a bull flag drifts slightly down before continuing up). Triangles (ascending, descending, symmetrical) show converging price action as a decision approaches. All of these generally resolve in the direction of the trend that preceded them, though a break can go either way — trade the break, not the assumption."},
                    {"heading": "Reversal patterns", "body": "Head-and-shoulders (a peak, a higher peak, then a lower peak — the mirror for inverse H&S) is one of the most cited reversal patterns; the 'neckline' break is the actual trigger, not the shoulder formation itself. Double tops/bottoms show price failing twice at the same level — the second failure, with weaker momentum than the first (often visible as bearish/bullish divergence), adds real weight to the signal."},
                    {"heading": "Measuring a target", "body": "A common technique: measure the height of the pattern (e.g., head to neckline in H&S, or the flagpole in a flag) and project that same distance from the breakout point. This gives a rough, not guaranteed, price target — useful for setting a reasonable take-profit rather than guessing arbitrarily."},
                ],
                "notes": [
                    "Flags/pennants/triangles are continuation patterns — they usually resolve with the prior trend.",
                    "Head-and-shoulders and double tops/bottoms are classic reversal patterns.",
                    "The neckline break (not the shoulder shape) is the actual H&S trigger.",
                    "Measure the pattern's height and project it from the breakout for a rough price target.",
                ],
                "quiz": [
                    {"q": "A bull flag typically:", "options": ["Slopes upward steeply during the pause", "Drifts slightly downward before resuming the prior uptrend", "Only appears in downtrends"], "answer": 1, "explanation": "The 'flag' portion is a shallow pullback against the trend, followed (in most cases) by continuation in the original direction."},
                    {"q": "In a head-and-shoulders pattern, the actual trade trigger is:", "options": ["The formation of the right shoulder", "The neckline break", "The head itself forming"], "answer": 1, "explanation": "The pattern isn't confirmed as a genuine reversal signal until price actually breaks the neckline — the shoulders alone are just the setup forming."},
                    {"q": "The standard way to estimate a chart pattern's price target is to:", "options": ["Guess based on the next round number", "Measure the pattern's height and project it from the breakout point", "Use the 200-day moving average"], "answer": 1, "explanation": "This 'measured move' technique gives a rough, structurally-grounded target rather than an arbitrary number."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Risk Management — Protect Your Capital",
        "description": "The one skill separating traders who last from traders who don't — position sizing, stop placement, and the discipline rules that stop a bad week becoming a blown account.",
        "category": "risk", "level": "beginner",
        "lessons": [
            {
                "title": "The 2% Rule & Why It Works",
                "summary": "Why professionals cap risk-per-trade well below what feels 'exciting' — and the math behind why that survives.",
                "duration": 7,
                "sections": [
                    {"heading": "The rule itself", "body": "Never risk more than 1-2% of your account balance on a single trade. On a $500 account at 2%, that's a $10 maximum loss per trade. It sounds conservative — almost boringly so — and that's exactly the point."},
                    {"heading": "The math of survival", "body": "At 2% risk per trade, you could lose 30 CONSECUTIVE trades and still have roughly 54% of your account left (0.98^30 ≈ 0.545). At 10% risk per trade, the same 30-loss streak leaves you with less than 5% of your account. Losing streaks happen to every strategy eventually — the position size determines whether you survive one intact or don't."},
                    {"heading": "Why beginners ignore it (and pay for it)", "body": "Small risk percentages feel unexciting when you're staring at a strong setup — the pull to 'just this once' risk more is one of the strongest urges in trading. But strategy edge is a long-run statistical property; a single oversized loss can undo dozens of correctly-sized wins."},
                ],
                "notes": [
                    "Cap risk per trade at 1-2% of current account balance, not a fixed dollar figure.",
                    "At 2% risk, a 30-trade losing streak still leaves ~54% of the account intact.",
                    "At 10% risk, the same streak leaves under 5% — the difference is survival itself.",
                    "Sizing up 'just this once' on a strong-feeling setup is one of the most common account-killers.",
                ],
                "quiz": [
                    {"q": "On a $500 account using the 2% rule, the maximum loss per trade is:", "options": ["$10", "$50", "$100"], "answer": 0, "explanation": "2% of $500 = $10 — that's the ceiling for how much a single trade should be allowed to cost you."},
                    {"q": "At 2% risk per trade, after 30 consecutive losses your account is roughly at:", "options": ["0% — completely wiped", "~54% of starting balance", "~90% of starting balance"], "answer": 1, "explanation": "0.98 raised to the 30th power ≈ 0.545 — meaning you'd still have over half your account, even after an extreme losing streak."},
                    {"q": "The 2% rule is calculated as a percentage of:", "options": ["Your very first deposit, forever", "Your current account balance", "Your broker's recommended amount"], "answer": 1, "explanation": "Risk is recalculated on the CURRENT balance each time — it naturally scales down after losses and up after gains, which is part of why it's self-protecting."},
                ],
            },
            {
                "title": "Position Sizing — The Actual Calculation",
                "summary": "The formula every trade should pass through before you click Buy or Sell — worked through with real numbers.",
                "duration": 10,
                "sections": [
                    {"heading": "The formula", "body": "Lot size = (Account balance × Risk %) ÷ (Stop-loss distance in pips × Pip value per lot). This single formula ties your account size, your risk tolerance, and your specific trade's stop distance together — it's the actual bridge between 'I want to risk 2%' and 'here's the exact lot size to enter.'"},
                    {"heading": "Worked example", "body": "$1,000 account, 2% risk = $20 max loss. Your analysis puts the stop-loss 25 pips away. On EUR/USD, a 0.01 lot (micro) is worth ~$0.10/pip, so a 0.10-lot position is worth ~$1.00/pip. $20 ÷ (25 pips × $1.00/pip... solving for lots) → you need roughly 0.08 lots to risk exactly $20 on a 25-pip stop."},
                    {"heading": "Why this beats 'gut feel' sizing", "body": "Without this calculation, position sizing tends to be an unconscious mix of confidence level and fear — bigger on trades that 'feel right,' smaller on ones you're unsure about. That's backwards: your actual analysis-driven confidence should determine whether you take the trade at all, and the FORMULA (not your feelings) should determine the size, every single time."},
                ],
                "notes": [
                    "Lot size = (Balance × Risk%) ÷ (SL pips × Pip value per lot).",
                    "Recalculate every trade — stop distance changes, so lot size must too.",
                    "This formula removes emotion from sizing — confidence decides IF you trade, the formula decides HOW MUCH.",
                    "A wider stop always means a smaller position size for the same dollar risk, and vice versa.",
                ],
                "quiz": [
                    {"q": "$1000 account, 2% risk, 25 pip SL on EUR/USD (0.01 lot ≈ $0.10/pip). Correct approximate lot size?", "options": ["0.01 lots", "0.08 lots", "0.20 lots"], "answer": 1, "explanation": "$20 risk ÷ 25 pips = $0.80/pip needed → at $0.10/pip per 0.01 lot, that's roughly 0.08 lots (8 micro lots)."},
                    {"q": "If your stop-loss distance gets wider (further from entry), your position size should:", "options": ["Get bigger to compensate", "Get smaller, to keep the same dollar risk", "Stay exactly the same"], "answer": 1, "explanation": "Dollar risk = pips × pip value × lots. If pips increase and dollar risk is fixed, lots must decrease proportionally."},
                    {"q": "What should primarily determine whether you enter a trade at all?", "options": ["How confident/excited you feel", "Your analysis and setup quality — sizing is calculated separately", "How big you can afford to go"], "answer": 1, "explanation": "The decision to trade should come from your analysis; the SIZE of that trade should come from the formula, not from how strongly you feel about it."},
                ],
            },
            {
                "title": "Where to Actually Place a Stop-Loss",
                "summary": "Structure-based stops vs. arbitrary pip counts — and the placements that match common setups.",
                "duration": 8,
                "sections": [
                    {"heading": "Structure, not superstition", "body": "A stop-loss should go where your trade IDEA is proven wrong — not at a round pip count you picked because it 'felt reasonable.' If you're buying a bounce off support, your idea is invalidated once price genuinely breaks below that support — so the stop belongs just past it, not at an arbitrary 20 pips regardless of where support actually sits."},
                    {"heading": "Common placements", "body": "Support/resistance bounce: SL 5-10 pips beyond the level (giving room for the normal 'wick through' noise). Pin bar/rejection candle: SL 3-5 pips beyond the wick tip. Breakout trade: SL just inside the broken level (so a false breakout that snaps back doesn't need to travel far to stop you out)."},
                    {"heading": "Never move a stop against you", "body": "Moving a stop-loss further away mid-trade to 'give it more room' after it's already moving against you is one of the most reliable ways to turn a normal, planned loss into a catastrophic one. If your original stop placement was wrong, that's a lesson for the NEXT trade's planning — not a reason to abandon the plan on the current one."},
                ],
                "notes": [
                    "Stops belong where the trade IDEA is invalidated, not at an arbitrary pip distance.",
                    "S/R bounce: SL 5-10 pips beyond the level. Pin bar: 3-5 pips beyond the wick.",
                    "Breakout trade: SL just inside the broken level.",
                    "Never widen a stop mid-trade to 'give it more room' — that's how small losses become large ones.",
                ],
                "quiz": [
                    {"q": "You buy a bounce at support. Where does the stop-loss belong?", "options": ["A fixed 20 pips, regardless of the setup", "5-10 pips below the support level", "At the previous swing high"], "answer": 1, "explanation": "The stop should sit just past where the support-bounce idea is actually proven wrong, with a small buffer for normal noise — not at an arbitrary distance."},
                    {"q": "Moving your stop-loss further away after a trade starts going against you is:", "options": ["A smart way to avoid small losses", "One of the most reliable ways to turn a planned loss into a large one", "Only risky on JPY pairs"], "answer": 1, "explanation": "It abandons the risk plan mid-trade based on hope, not analysis — a classic path from a normal, contained loss to a much larger one."},
                    {"q": "The core principle behind stop-loss placement is:", "options": ["Placing it wherever minimizes the pip count", "Placing it where your trade thesis is actually proven wrong", "Never using a stop-loss at all"], "answer": 1, "explanation": "A stop isn't just a number — it's the price level at which the reason you took the trade is no longer valid."},
                ],
            },
            {
                "title": "Risk:Reward & Expectancy",
                "summary": "The math that decides whether a strategy is actually profitable, independent of how often it wins.",
                "duration": 9,
                "sections": [
                    {"heading": "R:R basics", "body": "Risk:Reward compares how much you're risking to how much you're targeting. A 1:2 R:R risking 20 pips to target 40 pips means each winning trade earns twice what each losing trade costs. Minimum acceptable R:R for most strategies is around 1:1.5 to 1:2 — below that, win rate has to be very high just to break even."},
                    {"heading": "Expectancy — the real formula", "body": "Expectancy = (Win rate × Average win) − (Loss rate × Average loss). This is what actually determines long-run profitability, NOT win rate alone. A strategy winning only 35% of the time can still be strongly profitable at 1:3 R:R: (0.35 × 3R) − (0.65 × 1R) = 1.05R − 0.65R = +0.40R expectancy per trade, on average."},
                    {"heading": "Why chasing win rate alone is a trap", "body": "It's psychologically tempting to optimize for 'winning most of the time,' but a high win-rate strategy with poor R:R (e.g., winning 80% of the time but risking 3x what you target) can still be a losing strategy overall. Expectancy — not win rate — is the number that actually matters."},
                ],
                "notes": [
                    "Minimum acceptable R:R for most strategies: roughly 1:1.5 to 1:2.",
                    "Expectancy = (Win% × Avg win) − (Loss% × Avg loss) — this is the real profitability number.",
                    "A 35% win rate can be strongly profitable at 1:3 R:R.",
                    "Optimizing for win rate alone, ignoring R:R, is a common and costly trap.",
                ],
                "quiz": [
                    {"q": "With 1:2 R:R and a 40% win rate, is the strategy profitable?", "options": ["No — win rate is under 50%", "Yes — expectancy works out positive", "Impossible to know without more data"], "answer": 1, "explanation": "Expectancy = (0.40 × 2R) − (0.60 × 1R) = 0.80R − 0.60R = +0.20R per trade on average — profitable, despite a sub-50% win rate."},
                    {"q": "A strategy wins 80% of trades but risks 3 pips for every 1 pip targeted (R:R roughly 1:0.33). This strategy is:", "options": ["Definitely profitable because win rate is high", "Potentially unprofitable — needs the full expectancy math, not just win rate", "Impossible to lose money on"], "answer": 1, "explanation": "Expectancy ≈ (0.80 × 0.33R) − (0.20 × 1R) = 0.264R − 0.20R = only +0.064R — thin, and easily flipped negative by execution costs or a rough patch."},
                    {"q": "The single number that best determines a strategy's real long-run profitability is:", "options": ["Win rate alone", "Expectancy (combining win rate and R:R)", "Number of trades per day"], "answer": 1, "explanation": "Win rate alone is incomplete — expectancy accounts for both how often you win AND how much you win/lose each time."},
                ],
            },
            {
                "title": "Drawdown & Recovery Math",
                "summary": "Why losses and gains aren't symmetric — and what that means for how deep a drawdown you can tolerate.",
                "duration": 7,
                "sections": [
                    {"heading": "The asymmetry", "body": "Losing 10% of your account requires an 11.1% gain to get back to even. Losing 25% requires a 33% gain. Losing 50% requires a 100% gain just to break even. The deeper the drawdown, the disproportionately larger the recovery needed — this asymmetry is exactly why aggressive risk-per-trade is so dangerous over a long run of trades."},
                    {"heading": "Setting a personal drawdown limit", "body": "Many professional risk plans include a hard rule: if account drawdown reaches a set threshold (e.g., 15-20% from a peak), stop trading entirely and reassess — the strategy, the market conditions, or your own execution — rather than continuing to trade the same size through a deepening hole."},
                    {"heading": "Drawdown as a diagnostic, not just a number", "body": "A drawdown happening exactly as your backtested max-drawdown predicted is normal variance. A drawdown far exceeding backtested expectations, or coinciding with rule-breaking (moved stops, oversized trades, revenge trading) is a signal that something about EXECUTION broke down, not just market conditions."},
                ],
                "notes": [
                    "A 10% loss needs an 11.1% gain to recover; a 50% loss needs a 100% gain.",
                    "Recovery math gets disproportionately harder as drawdown deepens — this is why position sizing matters so much.",
                    "Many professional plans include a hard stop-trading threshold (e.g., 15-20% drawdown).",
                    "A drawdown coinciding with broken rules is a signal about execution, not just markets.",
                ],
                "quiz": [
                    {"q": "To recover from a 25% account loss, you need a gain of approximately:", "options": ["25%", "33%", "50%"], "answer": 1, "explanation": "If $100 drops to $75, you need $75 to grow back to $100 — a gain of $25/$75 ≈ 33.3%."},
                    {"q": "Why does this recovery math matter for position sizing?", "options": ["It doesn't relate to position sizing", "Because deeper drawdowns require disproportionately larger gains to recover — oversizing makes recovery mathematically harder", "Because brokers charge more after a drawdown"], "answer": 1, "explanation": "The asymmetry between loss % and required recovery % is exactly why keeping risk-per-trade small (avoiding deep drawdowns in the first place) is so important long-term."},
                    {"q": "A drawdown that coincides with moved stops and oversized trades most likely indicates:", "options": ["Normal market variance", "An execution/discipline breakdown, not just market conditions", "That the strategy should be doubled in size"], "answer": 1, "explanation": "When rule-breaking accompanies a drawdown, the deeper cause is often execution discipline, which is fixable — unlike pure market variance."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Trading Psychology",
        "description": "The mental game in depth — the biases that quietly sabotage good analysis, and the concrete systems that build real discipline instead of relying on willpower.",
        "category": "psychology", "level": "intermediate",
        "lessons": [
            {
                "title": "Fear & Greed — The Core Two",
                "summary": "How these two forces distort decisions at entry, during the trade, and at exit.",
                "duration": 8,
                "sections": [
                    {"heading": "Fear's fingerprints", "body": "Fear shows up as closing winners too early ('lock in the small gain before it disappears'), hesitating on valid setups after a recent loss, and moving stops closer out of anxiety rather than analysis. Fear optimizes for feeling safe RIGHT NOW, not for long-run expectancy."},
                    {"heading": "Greed's fingerprints", "body": "Greed shows up as holding losers too long ('it'll come back'), oversizing positions on a hot streak, and overtrading — taking marginal setups just to stay in the action. Greed optimizes for a bigger number NOW, at the cost of the discipline that made the good trades good in the first place."},
                    {"heading": "The fix: rules over feelings", "body": "Neither fear nor greed responds well to 'just be more disciplined.' What actually works is removing the in-the-moment decision: a written trading plan with fixed entry/exit/sizing rules decided BEFORE you're in a trade and emotionally invested. Follow the plan you wrote when you were calm, not the impulse you have when you're not."},
                ],
                "notes": [
                    "Fear: cutting winners early, hesitating after losses, moving stops closer out of anxiety.",
                    "Greed: holding losers too long, oversizing on hot streaks, overtrading for excitement.",
                    "Both optimize for how you feel right now, not for long-run expectancy.",
                    "A pre-written trading plan removes the in-the-moment emotional decision.",
                ],
                "quiz": [
                    {"q": "You're in a winning trade and feel a strong urge to close it early, before your plan's target. This is typically:", "options": ["Greed", "Fear", "Good instinct that should always be followed"], "answer": 1, "explanation": "Cutting a winner short out of anxiety about losing the gain is a classic fear response, not a disciplined analytical decision."},
                    {"q": "The most effective countermeasure to both fear and greed is:", "options": ["Trying harder to 'stay disciplined' in the moment", "A written plan with rules decided in advance, before emotional investment", "Trading smaller until the feelings go away"], "answer": 1, "explanation": "Pre-committing to rules while calm removes the need to make a good decision under emotional pressure — the plan decides, not the feeling."},
                    {"q": "Holding a losing trade well past your plan's stop-loss because 'it'll come back' is:", "options": ["Fear", "Greed / hope overriding the plan", "A valid technical strategy"], "answer": 1, "explanation": "This is a classic greed/hope pattern — refusing to accept a planned loss in the hope of a bigger recovery, which often leads to a much larger loss."},
                ],
            },
            {
                "title": "FOMO & Chasing the Market",
                "summary": "Why the fear of missing out leads directly to the worst-timed entries — and the mental reframe that fixes it.",
                "duration": 6,
                "sections": [
                    {"heading": "How FOMO operates", "body": "FOMO triggers when you watch a big move happen WITHOUT you in it. The instinct is to jump in immediately to 'not miss the rest' — but by definition, you're now entering after the move has already happened, often right as the early movers start taking profit."},
                    {"heading": "The math of chasing", "body": "Chasing typically means entering with a wider, worse-placed stop (because the clean structural levels are now far behind price) and a smaller realistic reward (because much of the move already happened). It inverts your risk:reward in exactly the wrong direction compared to catching the move at its actual origin."},
                    {"heading": "The reframe", "body": "There will always be another setup — genuinely, statistically, this is true over any meaningful stretch of time. The trader who consistently waits for the NEXT clean setup, rather than chasing the one that already left, ends up with a better average entry across a year of trading, even though it never feels that way in the single missed moment."},
                ],
                "notes": [
                    "FOMO entries happen AFTER a move, when the clean structural levels are already far away.",
                    "Chasing typically means a worse stop placement and reduced remaining reward.",
                    "There will always be another setup — this is statistically true, not just a comforting phrase.",
                    "Waiting for the next clean setup produces a better average entry over time than chasing.",
                ],
                "quiz": [
                    {"q": "EUR/USD just moved 80 pips without you in the trade. The disciplined response is usually to:", "options": ["Enter immediately at market to not miss more", "Wait for the next clean setup", "Double your usual size to make up for missing it"], "answer": 1, "explanation": "Entering after a large move already happened typically means a worse stop and reduced remaining reward — waiting for the next setup preserves better risk:reward."},
                    {"q": "Why does chasing a move usually worsen your risk:reward?", "options": ["It doesn't — R:R is unaffected by entry timing", "The clean structural stop levels are now far behind price, and much of the reward is already gone", "Chasing always uses smaller position sizes"], "answer": 1, "explanation": "A late entry forces a wider stop (since nearby structure is behind price) while the realistic remaining upside has shrunk — a worse combination than a clean, on-time entry."},
                ],
            },
            {
                "title": "Revenge Trading & Tilt",
                "summary": "Recognizing the specific psychological state that turns one loss into a string of much worse ones.",
                "duration": 7,
                "sections": [
                    {"heading": "What tilt looks like", "body": "'Tilt' (borrowed from poker) is the state after a loss (or a string of losses) where decision-making shifts from analytical to emotional — the trader is now trying to 'get the money back' rather than executing the next valid setup on its own merits. Trade quality typically drops sharply during tilt, even though the trader usually feels MORE confident, not less."},
                    {"heading": "The revenge-trading pattern", "body": "It typically escalates: a loss, followed by an oversized 'make it back' trade taken with less analysis than usual, followed (if that loses too) by an even larger position and even less patience for a valid setup. Each step further degrades judgment while increasing the stakes — a genuinely dangerous combination."},
                    {"heading": "The circuit breaker", "body": "The most effective countermeasure is a pre-committed rule, decided while calm: e.g. 'after 2-3 consecutive losses, I stop trading for the rest of the session/day, no exceptions.' This works precisely because it removes the decision from the moment when judgment is most compromised — you don't have to trust in-the-moment you to make a good call."},
                ],
                "notes": [
                    "Tilt shifts decision-making from analytical to emotional, usually while confidence rises, not falls.",
                    "Revenge trading escalates: bigger size, less analysis, less patience, each step after a loss.",
                    "A pre-committed 'stop after N losses' rule works because it removes the in-tilt decision entirely.",
                    "Trust the rule you set while calm, not the judgment you have while on tilt.",
                ],
                "quiz": [
                    {"q": "During 'tilt,' a trader's confidence typically:", "options": ["Drops sharply, making them cautious", "Often rises, even as decision quality drops", "Stays completely unaffected"], "answer": 1, "explanation": "A dangerous feature of tilt is that it often FEELS like conviction/confidence, even while the actual analytical quality behind the decisions has deteriorated."},
                    {"q": "The most effective way to prevent revenge trading is to:", "options": ["Rely on willpower in the moment after a loss", "Set a pre-committed 'stop after N losses' rule while calm, and follow it automatically", "Trade bigger to recover losses faster"], "answer": 1, "explanation": "Decisions made in advance, while calm, are far more reliable than decisions made in the emotionally compromised state right after a loss."},
                ],
            },
            {
                "title": "Building Real Discipline",
                "summary": "The concrete tools that create discipline as a system, rather than hoping for it as a personality trait.",
                "duration": 8,
                "sections": [
                    {"heading": "A written trading plan", "body": "A real trading plan specifies, in writing, BEFORE you're in a trade: what setups you take, what timeframes you trade, your risk per trade, your typical R:R target, and your session hours. Vague mental rules ('I'll trade good setups when I see them') don't survive contact with live emotion; specific written ones are far more likely to."},
                    {"heading": "A pre-trade checklist", "body": "A short checklist you run through before EVERY entry — is this aligned with the higher-timeframe bias? Is my stop at a structurally valid level? Is my position size correct for this stop distance? Am I trading because of a real setup, or because I'm bored/anxious/chasing? A checklist catches the mistakes discipline alone often misses."},
                    {"heading": "A trading journal", "body": "Logging every trade (entry/exit reasoning, emotional state, outcome) turns scattered individual experiences into visible PATTERNS over time — which setups actually work for you, which times of day you make your worst decisions, which emotional states precede your biggest mistakes. Review it weekly; the patterns rarely show up after just one or two trades, but become obvious after twenty or thirty."},
                ],
                "notes": [
                    "A written plan (setups, timeframes, risk, R:R, hours) beats vague mental rules.",
                    "A pre-trade checklist catches mistakes that willpower alone tends to miss.",
                    "A trading journal turns scattered experiences into visible, actionable patterns.",
                    "Review the journal weekly — patterns emerge over dozens of trades, not one or two.",
                ],
                "quiz": [
                    {"q": "The most effective tool for identifying your own recurring trading mistakes over time is:", "options": ["Trading more frequently", "A trading journal, reviewed regularly", "Increasing position sizes"], "answer": 1, "explanation": "A journal converts scattered individual trades into a dataset you can actually analyze for patterns — which mistakes repeat, and under what conditions."},
                    {"q": "A pre-trade checklist is useful mainly because it:", "options": ["Guarantees every trade wins", "Catches process mistakes (sizing, alignment, motivation) that discipline alone tends to miss", "Is required by brokers"], "answer": 1, "explanation": "It's a structural safeguard — running through it before every entry catches the kind of slip-ups that 'just be disciplined' alone often fails to prevent."},
                ],
            },
            {
                "title": "Process Over Outcome",
                "summary": "The mental shift that separates traders who improve from traders who just react to their last trade's result.",
                "duration": 7,
                "sections": [
                    {"heading": "Why outcome-based judgment is misleading", "body": "Even the best traders and strategies lose a meaningful fraction of trades — often 35-50%, depending on style. Judging a single trade purely by whether it won or lost ignores that a well-executed trade following your rules can still lose (normal variance), while a badly-executed trade can still win (luck)."},
                    {"heading": "The reframe", "body": "A loss that followed your rules — correct setup, correct size, correct stop placement — is a GOOD trade with a bad outcome. A win that broke your rules — oversized, no real setup, moved stop — is a BAD trade with a good outcome. Over enough trades, following good process reliably produces good outcomes; a single instance doesn't prove or disprove anything on its own."},
                    {"heading": "What this changes in practice", "body": "This reframe changes what you actually review after a trade: not 'did I win or lose' but 'did I follow my process.' It also reduces the emotional whiplash of individual trades — a rule-following loss doesn't need to feel like a personal failure, and a rule-breaking win shouldn't feel like validation to keep breaking rules."},
                ],
                "notes": [
                    "Even top traders lose 35-50%+ of trades — that alone doesn't mean a mistake was made.",
                    "A rule-following loss is a GOOD trade with a bad outcome, not a failure.",
                    "A rule-breaking win is a BAD trade with a good outcome — don't let it validate the rule-break.",
                    "Review process, not just win/loss — that's what actually drives improvement over time.",
                ],
                "quiz": [
                    {"q": "A trade hits your stop-loss after you followed every rule correctly. This was:", "options": ["A bad trade — you should have avoided it", "A good trade with a bad outcome — normal variance", "Proof your strategy doesn't work"], "answer": 1, "explanation": "Following your process correctly and still losing is expected some percentage of the time — it doesn't by itself indicate a mistake or a broken strategy."},
                    {"q": "What should you primarily review after each trade to actually improve?", "options": ["Only whether it won or lost", "Whether you followed your process/rules, regardless of outcome", "How much money you made or lost that specific day"], "answer": 1, "explanation": "Process quality, reviewed consistently, is what improves over time and drives good outcomes across many trades — outcome alone on a single trade is a noisy, misleading signal."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Advanced: Copy Trading & Automation",
        "description": "How to evaluate providers with real rigor, size copy-risk correctly, and understand exactly what's happening when a trade auto-copies into your account.",
        "category": "advanced", "level": "advanced",
        "lessons": [
            {
                "title": "How Copy Trading Actually Works",
                "summary": "The mechanics behind provider trades replicating into a follower's account — and what stays under your control.",
                "duration": 7,
                "sections": [
                    {"heading": "The replication mechanism", "body": "When a provider opens a trade, the platform detects it and replicates it into each follower's account — but NOT at identical size. Your position is scaled to YOUR account and YOUR risk settings, not copied at the provider's raw lot size. A provider trading 1.0 lots on a $50,000 account and you following on a $500 account at the same 1.0 lots would be wildly, dangerously oversized."},
                    {"heading": "What you still control", "body": "Even with auto-copy enabled, your own settings govern: risk per copied trade (typically 1-2% of YOUR balance), a minimum confidence/quality filter (only copy signals above a threshold), a pairs filter (only copy instruments you understand), and a max lot cap (an absolute ceiling regardless of what the formula suggests)."},
                    {"heading": "SL/TP and manual adjustment", "body": "A copied trade arrives with the provider's stop-loss and take-profit levels (scaled proportionally to price, not literally identical numbers across different account currencies/pairs). You can still manually adjust SL/TP on a copied trade after it opens — useful if your own risk tolerance or read of the market differs from the provider's, though doing this on every trade somewhat defeats the purpose of copying in the first place."},
                ],
                "notes": [
                    "Your copied position is sized to YOUR account/settings, never at the provider's raw lot size.",
                    "You control: risk %, minimum confidence filter, pairs filter, and max lot cap.",
                    "SL/TP arrive scaled from the provider's trade but can be manually adjusted afterward.",
                    "Constantly overriding every copied trade's SL/TP undermines the point of copying.",
                ],
                "quiz": [
                    {"q": "In copy trading, your position size should be:", "options": ["Identical to the provider's raw lot size", "Proportional to your own account size and risk settings", "Always fixed at 0.01 lots"], "answer": 1, "explanation": "Copying the provider's raw lot size regardless of account size would produce wildly mismatched risk — the platform scales trades to each follower's own account and settings."},
                    {"q": "Which of these do you still control as a follower, even with auto-copy on?", "options": ["Nothing — it's fully automatic", "Risk per trade, minimum confidence filter, pairs filter, and max lot cap", "Only whether the platform charges a fee"], "answer": 1, "explanation": "Auto-copy automates the EXECUTION of matching trades, but your risk parameters and filters still govern how much and what actually gets copied."},
                ],
            },
            {
                "title": "Evaluating a Provider Rigorously",
                "summary": "The specific metrics that separate a genuinely skilled provider from one who's about to blow up.",
                "duration": 10,
                "sections": [
                    {"heading": "The core metrics", "body": "Win rate above ~55% is a reasonable baseline (not a guarantee), Risk:Reward averaging 1:2 or better, maximum drawdown under roughly 20%, and a MINIMUM of 100+ signals of history — smaller samples are statistically close to meaningless. Consistent monthly pips over many months matters more than one spectacular month."},
                    {"heading": "Red flags", "body": "Under 3 months of history (not enough data to judge), drawdown above 30% (a sign of poor risk control, even if returns look good), and — the classic trap — a suspiciously high win rate like 90%+. Extremely high win rates are usually achieved by taking on huge, hidden tail risk (very wide stops or no stops at all), meaning one bad trade can erase months of 'wins.'"},
                    {"heading": "Reading drawdown, not just returns", "body": "Two providers can show the same 12-month return, but one achieved it with a max 12% drawdown and the other with a max 45% drawdown. The second took roughly 3-4x more risk to get the SAME return — meaningfully worse risk-adjusted performance, even though the headline number looks identical."},
                ],
                "notes": [
                    "Baseline metrics: win rate >55%, R:R ≥1:2, max drawdown <20%, 100+ signal history.",
                    "Red flags: <3 months history, >30% drawdown, suspiciously high (90%+) win rates.",
                    "A 90%+ win rate often hides huge tail risk from very wide/absent stops.",
                    "Compare drawdown, not just returns — the same return with less drawdown is genuinely better.",
                ],
                "quiz": [
                    {"q": "A provider shows a 95% win rate over 50 trades. The correct response is:", "options": ["Subscribe immediately — that's an amazing win rate", "Be very suspicious — this is very likely hiding large tail risk, and 50 trades is a thin sample", "Ignore win rate entirely, it never matters"], "answer": 1, "explanation": "Extremely high win rates are usually achieved via very wide or absent stops, meaning a single bad trade can erase months of gains — and 50 trades is too small a sample to trust anyway."},
                    {"q": "Two providers have identical 12-month returns, but Provider A's max drawdown was 12% and Provider B's was 45%. Which is the better risk-adjusted performer?", "options": ["Provider B — same return either way", "Provider A — same return with far less risk taken", "Impossible to compare"], "answer": 1, "explanation": "Achieving the same return with much less drawdown means Provider A generated that return more efficiently and with less risk to the follower's capital."},
                    {"q": "Why is a minimum of 100+ signals of history important before trusting a provider's stats?", "options": ["It's an arbitrary platform requirement", "Smaller samples are statistically close to meaningless — a hot streak can look like skill", "100 is required by regulation"], "answer": 1, "explanation": "With small sample sizes, luck and skill are hard to distinguish — a real edge only becomes statistically visible over a meaningfully large number of trades."},
                ],
            },
            {
                "title": "Sizing Copy-Trade Risk Correctly",
                "summary": "Setting risk-per-copy-trade, confidence filters, and lot caps that fit YOUR account, not the provider's.",
                "duration": 8,
                "sections": [
                    {"heading": "Risk per copy trade", "body": "The same 1-2% principle from standalone risk management applies directly to copy trading — arguably more so, since you're trusting someone else's entry/exit decisions on top of the market's own uncertainty. A beginner on a small account copying at 5-10% per trade is taking on outsized risk regardless of how skilled the provider actually is."},
                    {"heading": "Confidence/quality filters", "body": "Most copy platforms let you set a minimum confidence score (e.g. only copy signals rated 65+) — this filters out the provider's own lower-conviction trades, which tend to have worse statistics than their top-conviction setups. It's a reasonable way to get more of a provider's BEST trades and fewer of their marginal ones."},
                    {"heading": "Max lot cap as a hard ceiling", "body": "Even with correct percentage-based sizing, an absolute max lot cap protects against edge cases — a provider's sudden large trade during unusual volatility, or a formula edge case producing an unexpectedly large calculated size. Think of it as a seatbelt on top of the main risk system, not a replacement for it."},
                ],
                "notes": [
                    "Apply the same 1-2% risk principle to copy trades as to any trade you'd take yourself.",
                    "A minimum confidence filter tends to capture a provider's best trades, not their marginal ones.",
                    "A max lot cap is a hard ceiling/seatbelt on top of percentage-based sizing, not a replacement for it.",
                    "Copying at high risk % doesn't become safer just because someone else made the entry decision.",
                ],
                "quiz": [
                    {"q": "Best approximate risk % per copy trade for a small beginner account?", "options": ["5-10%", "1-2%", "0.1%, essentially nothing"], "answer": 1, "explanation": "The same disciplined risk-per-trade principle applies to copy trading — trusting a provider's decisions doesn't reduce the need for sound position sizing."},
                    {"q": "A minimum confidence filter on copy trades primarily helps by:", "options": ["Guaranteeing every copied trade wins", "Filtering toward the provider's higher-conviction (typically better-performing) setups", "Reducing the platform's fees"], "answer": 1, "explanation": "It's not a guarantee, but higher-conviction signals from a provider tend to statistically outperform their lower-conviction ones — the filter shifts your copied mix toward the better trades."},
                ],
            },
            {
                "title": "MT5 Bridge Execution — What Changes",
                "summary": "The difference between simulated copy trading and live execution through an MT5 Expert Advisor bridge.",
                "duration": 9,
                "sections": [
                    {"heading": "Simulated vs. live execution", "body": "Simulated copy trading tracks trades and P&L on the platform without touching a real brokerage account — useful for evaluation and learning without financial risk. Live execution via an MT5 bridge actually places real orders in your real MT5 account through an Expert Advisor (EA) that listens for copy signals and executes them."},
                    {"heading": "Setting up the bridge", "body": "This typically requires: a real MT5 account with a broker, installing the platform's EA on your MT5 terminal, and linking your MT5 login credentials to the platform (handled securely — never share your MT5 investor password casually). Once linked, the bridge status should show 'connected' before you enable live execution."},
                    {"heading": "Testing before going live", "body": "Test on a demo MT5 account for at least 30 days before connecting a real-money account. This surfaces execution issues (slippage, requotes, connectivity gaps) and lets you observe how the bridge actually behaves with your specific broker's conditions — which can meaningfully differ from the simulated numbers you saw during evaluation."},
                ],
                "notes": [
                    "Simulated copy trading has no real money at risk; MT5 bridge execution places real orders.",
                    "Setup requires a real MT5 account, the platform's EA installed, and credentials linked securely.",
                    "Bridge status should show 'connected' before enabling live execution.",
                    "Always test on a demo MT5 account for 30+ days before connecting real money.",
                ],
                "quiz": [
                    {"q": "The key difference between simulated and MT5-bridge copy trading is:", "options": ["Simulated is more accurate", "MT5-bridge execution places real orders in your actual brokerage account", "There is no real difference"], "answer": 1, "explanation": "Simulated copy trading tracks hypothetical P&L; the MT5 bridge actually executes real trades through your connected broker account via an Expert Advisor."},
                    {"q": "Before connecting a real-money MT5 account for live copy execution, you should:", "options": ["Go live immediately for the best results", "Test on a demo account for at least 30 days first", "Skip testing if the provider looks good"], "answer": 1, "explanation": "Demo testing surfaces broker-specific execution behavior (slippage, requotes, connectivity) that simulated numbers alone won't reveal."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Advanced Price Action & Chart Patterns",
        "description": "No indicators — trading purely from what price itself is telling you: market structure, liquidity, order blocks, and breaker patterns used by institutional-style traders.",
        "category": "advanced", "level": "advanced",
        "lessons": [
            {
                "title": "Market Structure: HH, HL, LH, LL",
                "summary": "The vocabulary institutions actually use to describe trend, and the exact moment a trend is considered 'broken'.",
                "duration": 9,
                "sections": [
                    {"heading": "Defining trend by swing points", "body": "An uptrend is a sequence of Higher Highs (HH) and Higher Lows (HL) — each swing high exceeds the last, each pullback low stays above the prior low. A downtrend is the mirror: Lower Highs (LH) and Lower Lows (LL). This is a more precise, less subjective definition of 'trend' than eyeballing a moving average's slope."},
                    {"heading": "Break of structure (BOS)", "body": "A Break of Structure occurs when price takes out the most recent swing point in the direction of the existing trend — e.g., in an uptrend, breaking above the last HH confirms trend continuation. BOS is used as ongoing confirmation that the trend remains intact, trade after trade."},
                    {"heading": "Change of character (CHoCH)", "body": "A Change of Character is the first structural sign a trend may be ending — e.g., in an uptrend, price fails to make a new HH and instead breaks BELOW the most recent HL. This is the earliest objective structural warning of a potential reversal, well before a lagging indicator would confirm it."},
                ],
                "notes": [
                    "Uptrend = sequence of Higher Highs + Higher Lows. Downtrend = Lower Highs + Lower Lows.",
                    "Break of Structure (BOS) = trend continuation confirmed by a new swing point in the trend's direction.",
                    "Change of Character (CHoCH) = the first structural break AGAINST the trend — an early reversal warning.",
                    "This framework defines trend/reversal objectively from swing points, not indicator lag.",
                ],
                "quiz": [
                    {"q": "An uptrend is defined structurally as a sequence of:", "options": ["Lower highs and lower lows", "Higher highs and higher lows", "Equal highs and equal lows"], "answer": 1, "explanation": "Each new swing high exceeding the last, and each pullback low staying above the prior low, is the structural definition of an uptrend."},
                    {"q": "A 'Change of Character' (CHoCH) in an uptrend occurs when:", "options": ["Price makes a new higher high", "Price breaks below the most recent higher low, failing to make a new high first", "Volume increases"], "answer": 1, "explanation": "CHoCH is the first sign the established pattern of higher highs/higher lows is breaking down — an early, objective reversal warning."},
                    {"q": "A 'Break of Structure' in the direction of the existing trend indicates:", "options": ["A likely reversal", "Trend continuation being confirmed", "A sideways range forming"], "answer": 1, "explanation": "BOS specifically means the trend just confirmed itself again by making a new swing point in its own direction."},
                ],
            },
            {
                "title": "Liquidity — Where Stops Actually Cluster",
                "summary": "Why price often runs just past an 'obvious' level before reversing — and how to read that instead of being caught by it.",
                "duration": 9,
                "sections": [
                    {"heading": "Liquidity pools", "body": "Stop-losses and pending orders cluster just beyond obvious swing highs/lows — buy stops above resistance/recent highs, sell stops below support/recent lows. This is why the level, and the small zone just past it, becomes an attractive target for larger participants — there's real order flow ('liquidity') sitting there to be absorbed."},
                    {"heading": "Stop hunts / liquidity sweeps", "body": "A 'stop hunt' or liquidity sweep is when price pushes just beyond an obvious level — triggering the stops/orders clustered there — before reversing sharply back the other way. It's not literally a conspiracy against retail traders; it's larger participants using the liquidity that clustering itself created as fuel to enter their own position at a good price."},
                    {"heading": "Trading around liquidity, not into it", "body": "Practical implication: placing a stop-loss at the exact 'obvious' level (right at a round number or the precise prior swing point) puts you in the most crowded, most likely-to-be-swept zone. Placing it a bit further past the obvious level, or using a slightly less obvious level, can meaningfully reduce the odds of being caught in a sweep that then reverses in your original direction anyway."},
                ],
                "notes": [
                    "Buy stops cluster above resistance/recent highs; sell stops cluster below support/recent lows.",
                    "A liquidity sweep pushes just past an obvious level (triggering those stops) before reversing.",
                    "It reflects order-flow mechanics, not a conspiracy — clustered stops are genuine liquidity to absorb.",
                    "Placing stops at the most 'obvious' exact level puts you in the most commonly swept zone.",
                ],
                "quiz": [
                    {"q": "Buy-stop orders tend to cluster:", "options": ["Below support levels", "Above resistance/recent swing highs", "Randomly throughout the chart"], "answer": 1, "explanation": "Traders placing stops for short positions, and breakout buyers' pending orders, both tend to sit just above recent highs/resistance."},
                    {"q": "A 'liquidity sweep' is best understood as:", "options": ["A broker manipulating your specific account", "Price pushing past an obvious level to trigger clustered orders, often reversing afterward", "A technical glitch in the platform"], "answer": 1, "explanation": "It's a market-wide order-flow phenomenon — larger participants use the resting liquidity beyond obvious levels, not an attack on any individual trader."},
                    {"q": "Placing a stop-loss at the exact 'obvious' round-number level tends to:", "options": ["Guarantee protection from a sweep", "Put you in the most crowded, most commonly swept zone", "Have no effect either way"], "answer": 1, "explanation": "The most obvious level is exactly where the most orders cluster — making it a common target for a sweep before price reverses."},
                ],
            },
            {
                "title": "Order Blocks & Supply/Demand Zones",
                "summary": "Identifying the specific candles that mark where large orders were likely placed, and how to trade a return to them.",
                "duration": 10,
                "sections": [
                    {"heading": "What an order block is", "body": "An order block is typically the last opposing candle before a strong, decisive move — e.g., the last down-candle before a sharp rally is a bullish order block, theorized to be where large buy orders were absorbed before pushing price up. The idea: if price returns to that zone later, similar buying interest may reappear there."},
                    {"heading": "Supply and demand zones", "body": "Closely related: a demand zone is a price area where buying previously overwhelmed selling, causing a sharp rally away from it (often identified by a tight consolidation just before the move — the 'base'). A supply zone is the mirror for a sharp decline. Both are drawn as a small range (the base), not a single line."},
                    {"heading": "Trading a return to the zone", "body": "The typical approach: mark the zone after the strong move away from it, then wait for price to return (a pullback) into that zone, and look for confirmation (a rejection candle, momentum shift) before entering in the original direction. The FIRST return to a fresh zone is generally considered more reliable than the third or fourth — each retest can weaken the zone, similar to any S/R level."},
                ],
                "notes": [
                    "An order block is typically the last opposing candle before a strong, decisive move.",
                    "Demand/supply zones are drawn as the small consolidation ('base') just before the move, not one line.",
                    "The typical trade waits for a pullback INTO the zone, then confirmation, before entering.",
                    "The first retest of a fresh zone is generally more reliable than later retests.",
                ],
                "quiz": [
                    {"q": "A bullish order block is typically identified as:", "options": ["The candle with the largest volume in an uptrend", "The last down-candle immediately before a strong rally", "Any green candle"], "answer": 1, "explanation": "The theory is that this last opposing candle marks where significant buy orders were absorbed just before price pushed sharply higher."},
                    {"q": "The standard approach to trading a demand zone is to:", "options": ["Enter immediately when the zone first forms, mid-rally", "Wait for price to pull back into the zone, then look for confirmation before entering", "Only trade the zone after it's been retested 5+ times"], "answer": 1, "explanation": "The zone marks a level where buying interest may reappear on a RETURN visit — entering at formation, mid-move, skips the actual setup."},
                    {"q": "Compared to later retests, the FIRST retest of a fresh order block/zone is generally considered:", "options": ["Less reliable", "More reliable", "Exactly equally reliable"], "answer": 1, "explanation": "Similar to standard S/R, each retest can consume some of the resting interest at a level — the first fresh retest tends to be the strongest."},
                ],
            },
            {
                "title": "Breaker Blocks & Failed Structure",
                "summary": "What happens (and why it matters) when an order block fails, and how the failure itself becomes a new signal.",
                "duration": 8,
                "sections": [
                    {"heading": "When an order block fails", "body": "Sometimes price returns to an order block/demand zone and, instead of holding, breaks straight through it — invalidating the zone as support. This isn't just 'the setup didn't work' and nothing more; the FAILURE itself can flip into a new signal in the opposite direction, called a breaker block."},
                    {"heading": "The breaker block concept", "body": "Once a demand zone is broken through decisively, the theory holds that it can flip into a new SUPPLY zone on a retest from below — similar to the classic support-flips-to-resistance idea, but applied specifically to these order-flow-based zones rather than simple horizontal S/R lines."},
                    {"heading": "Why failure-based signals need extra confirmation", "body": "Breaker-block setups are a step more speculative than fresh order blocks — they rely on a chain of two assumptions (the original zone theory, plus the flip theory) instead of one. Treat them as a lower-conviction setup requiring more confluence (higher-timeframe alignment, additional structure) before sizing a trade around one."},
                ],
                "notes": [
                    "A failed order block (broken through decisively) can flip into a 'breaker block' — a new zone in the opposite direction.",
                    "This mirrors the classic support-flips-to-resistance idea, applied to order-flow-based zones.",
                    "Breaker setups rest on two chained assumptions, making them lower-conviction than a fresh order block.",
                    "Require extra confluence before trading a breaker-block setup at meaningful size.",
                ],
                "quiz": [
                    {"q": "When a demand zone is decisively broken through rather than holding, this can theoretically become:", "options": ["Meaningless — just ignore it and move on", "A 'breaker block' — a new zone in the opposite direction", "Proof the entire strategy doesn't work"], "answer": 1, "explanation": "The failure itself is treated as informative — the broken demand zone can flip into a new supply zone on a later retest from below."},
                    {"q": "Compared to a fresh order block, a breaker-block setup is generally:", "options": ["Higher conviction, since it already failed once", "Lower conviction, since it relies on two chained assumptions", "Identical in reliability"], "answer": 1, "explanation": "It requires both the original zone theory and the flip-on-failure theory to hold — more assumptions stacked together than a single fresh zone."},
                ],
            },
            {
                "title": "Fair Value Gaps & Imbalance",
                "summary": "Reading the 'gaps' left behind by fast, one-directional moves, and why price often revisits them.",
                "duration": 8,
                "sections": [
                    {"heading": "What a fair value gap is", "body": "A Fair Value Gap (FVG), also called an imbalance, forms when price moves so fast in one direction that a visible gap is left between candle 1's wick and candle 3's wick (candle 2 being the big impulsive move) — meaning there's a price range with comparatively few two-sided trades (buyers AND sellers both active) at those levels, mostly one-sided aggression instead."},
                    {"heading": "Why price often returns to fill it", "body": "The theory: because that range lacks 'fair,' two-sided price discovery, price has a tendency to return and 'fill' at least part of the gap later, effectively letting the market retrade that zone properly before continuing. This isn't guaranteed on every gap, but it's observed often enough to be a widely used concept."},
                    {"heading": "Using FVGs as targets and entries", "body": "FVGs get used two ways: as a TARGET (a likely magnet for price to be drawn back toward), and as an ENTRY zone (waiting for a pullback into an FVG in the direction of the prevailing trend, similar to trading a pullback into an order block). As with all these zone-based concepts, confluence with higher-timeframe structure meaningfully improves the odds."},
                ],
                "notes": [
                    "An FVG/imbalance is the gap left between candle 1 and candle 3's wicks around a fast, one-directional move.",
                    "It represents a price range with limited two-sided trading — mostly one-directional aggression.",
                    "Price often (not always) returns to at least partially fill an FVG later.",
                    "FVGs are used both as price targets and as pullback entry zones, ideally with higher-timeframe confluence.",
                ],
                "quiz": [
                    {"q": "A Fair Value Gap forms when:", "options": ["Price consolidates tightly for many candles", "A fast, impulsive move leaves a visible gap between the wicks of the first and third candle in the sequence", "The market is closed for the weekend"], "answer": 1, "explanation": "The rapid one-directional move (the middle candle) leaves behind a range with limited two-sided trading, visible as a gap between the outer candles' wicks."},
                    {"q": "The common theory about why price often returns to an FVG later is:", "options": ["It's a random coincidence with no explanation", "The range lacked two-sided 'fair' price discovery, and the market tends to retrade it", "FVGs always predict a full trend reversal"], "answer": 1, "explanation": "Because the initial move was mostly one-sided, the theory holds that the market has an inclination to revisit and 'fill in' that price discovery gap, at least partially."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Fibonacci, Elliott Wave & Harmonic Trading",
        "description": "Advanced mathematical trading tools — retracement/extension levels, wave counting, and harmonic patterns like Gartley and Bat, used to project where price is likely headed next.",
        "category": "technical", "level": "advanced",
        "lessons": [
            {
                "title": "Fibonacci Retracement Levels",
                "summary": "Where the key ratios come from, and which levels actually earn the most attention from traders.",
                "duration": 8,
                "sections": [
                    {"heading": "Where the ratios come from", "body": "Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) are derived from the Fibonacci sequence's mathematical ratios. Applied to a price swing, they mark potential pullback levels before the prior trend resumes. 50% isn't technically a Fibonacci ratio at all, but it's included by near-universal convention because psychologically 'half the move' matters to traders regardless of the math."},
                    {"heading": "The 'golden pocket'", "body": "The zone between 61.8% and 65% retracement — sometimes called the 'golden pocket' — gets outsized attention because 61.8% (the golden ratio's inverse) is considered the most significant single Fib level. A pullback that reaches this zone and shows a reversal signal is a commonly watched setup."},
                    {"heading": "Why it works (probably)", "body": "Fibonacci levels don't have an underlying market 'mechanism' the way order flow or S/R do — their effectiveness is largely attributed to self-fulfilling behavior: because so many traders watch and act around the same levels, those levels genuinely do attract orders and reactions, regardless of the deeper mathematical justification."},
                ],
                "notes": [
                    "Key retracement levels: 23.6%, 38.2%, 50% (convention, not true Fib), 61.8%, 78.6%.",
                    "The 61.8%-65% 'golden pocket' is the most closely watched retracement zone.",
                    "Fib levels work largely because so many traders watch and act around them — a self-fulfilling dynamic.",
                    "Use Fib levels as confluence with structure/candlesticks, not as a standalone signal.",
                ],
                "quiz": [
                    {"q": "The 'golden pocket' refers to the zone between:", "options": ["23.6% and 38.2%", "61.8% and 65%", "0% and 23.6%"], "answer": 1, "explanation": "This zone around the golden-ratio-derived 61.8% level is the most heavily watched Fibonacci retracement area."},
                    {"q": "Why do Fibonacci levels tend to 'work' as reaction points?", "options": ["A proven physical law of markets", "Largely self-fulfilling — enough traders watch/act on the same levels that they attract real orders", "They don't work at all, ever"], "answer": 1, "explanation": "Unlike order-flow-based concepts, Fib levels lack a clear underlying market mechanism — their usefulness comes largely from widespread collective attention on the same price points."},
                ],
            },
            {
                "title": "Fibonacci Extensions & Price Targets",
                "summary": "Projecting how far a move might travel BEYOND the prior swing, once a retracement has completed.",
                "duration": 7,
                "sections": [
                    {"heading": "Extension vs. retracement", "body": "Retracement measures a PULLBACK within an existing move (0-100% of the prior swing). Extension projects a target BEYOND the prior swing (127.2%, 161.8%, 261.8%) — used once a retracement has completed and the trend is expected to resume, to estimate how far the NEXT leg might travel."},
                    {"heading": "The 161.8% level", "body": "161.8% extension is the most commonly used target, again tied to the golden ratio. It's frequently used to set take-profit targets for trend-continuation trades entered at a Fibonacci retracement level — combining the retracement entry with an extension-based exit in a single coherent framework."},
                    {"heading": "Combining with structure", "body": "As with retracements, extension targets are far more useful when they line up with independent evidence — e.g., a 161.8% extension target that also happens to sit right at a prior swing high (an S/R level from a totally different method) gives two independent reasons to expect a reaction there, rather than relying on Fibonacci math alone."},
                ],
                "notes": [
                    "Retracement measures pullback within a move; extension projects beyond the prior swing.",
                    "Key extension levels: 127.2%, 161.8%, 261.8% — with 161.8% most commonly used.",
                    "Extensions are often combined with retracement entries for a full entry-to-target framework.",
                    "Extension targets aligning with independent structure (S/R) are more reliable than Fib math alone.",
                ],
                "quiz": [
                    {"q": "Fibonacci extension levels are used to:", "options": ["Measure a pullback within the current move", "Project a target beyond the prior swing, for the next leg of the trend", "Identify the exact market open time"], "answer": 1, "explanation": "Extensions look forward past the prior high/low to estimate how far a resumed trend might travel."},
                    {"q": "An extension target is most reliable when:", "options": ["Used completely alone with no other confirmation", "It aligns with independent structure, like a prior swing high acting as resistance", "It's below the current price"], "answer": 1, "explanation": "Confluence between the Fibonacci-derived target and an independently-identified structural level strengthens the case that price may react there."},
                ],
            },
            {
                "title": "Elliott Wave Basics",
                "summary": "The 5-3 wave structure that describes market cycles as a repeating psychological pattern, not just price noise.",
                "duration": 10,
                "sections": [
                    {"heading": "The 5-wave impulse", "body": "Elliott Wave theory holds that trending moves unfold in 5 waves: waves 1, 3, and 5 move WITH the trend; waves 2 and 4 are corrective pullbacks against it. Two structural rules: wave 2 never retraces beyond the start of wave 1, and wave 3 is never the shortest of waves 1, 3, and 5 — these rules help distinguish a valid count from an invalid one."},
                    {"heading": "The 3-wave correction", "body": "After the 5-wave impulse completes, a 3-wave corrective structure (labeled A-B-C) typically follows, retracing part of the impulse before the next impulse (in the same or opposite larger-degree trend) begins. This alternation between 5-wave impulses and 3-wave corrections is the core repeating rhythm the theory describes."},
                    {"heading": "Fractal nature and its main weakness", "body": "Elliott Wave is fractal — each of the 5 impulse waves can itself be broken down into its own smaller 5-wave (or 3-wave, for corrective waves) structure, at a smaller timeframe. This is also the theory's most-criticized weakness: because wave counts can often be interpreted multiple valid ways in real time, it's considerably more subjective than something like moving-average crossovers, and different analysts frequently disagree on the current count."},
                ],
                "notes": [
                    "Impulse = 5 waves (1,3,5 with trend; 2,4 corrective against it). Correction = 3 waves (A-B-C).",
                    "Rule: wave 2 never retraces past the start of wave 1. Rule: wave 3 is never the shortest of 1/3/5.",
                    "The structure is fractal — each wave subdivides into its own smaller wave count.",
                    "Its main weakness: wave counts are often genuinely ambiguous/subjective in real time.",
                ],
                "quiz": [
                    {"q": "In a standard Elliott Wave impulse, which waves move WITH the larger trend?", "options": ["Waves 2 and 4", "Waves 1, 3, and 5", "Only wave 3"], "answer": 1, "explanation": "Waves 1, 3, and 5 are the impulsive (trend-direction) waves; waves 2 and 4 are corrective pullbacks against the trend."},
                    {"q": "A core Elliott Wave rule states that:", "options": ["Wave 3 can be the shortest of waves 1, 3, and 5", "Wave 2 can never retrace beyond the start of wave 1", "Waves must always be exactly equal in length"], "answer": 1, "explanation": "If a proposed wave 2 retraces past the very start of wave 1, the count is invalid by Elliott Wave's own rules."},
                    {"q": "The most commonly cited weakness of Elliott Wave analysis is:", "options": ["It's too mathematically precise", "Wave counts are often genuinely ambiguous, leading analysts to disagree", "It only works on the daily timeframe"], "answer": 1, "explanation": "Because real price action can often be validly counted more than one way in real time, Elliott Wave is considerably more subjective than many other technical tools."},
                ],
            },
            {
                "title": "Harmonic Patterns: Gartley & Bat",
                "summary": "Geometric price patterns built from precise Fibonacci ratios at each leg — and the PRZ they converge on.",
                "duration": 9,
                "sections": [
                    {"heading": "The harmonic concept", "body": "Harmonic patterns are 5-point price structures (labeled X-A-B-C-D) where each leg must fall within specific Fibonacci ratio ranges relative to the others. Unlike a loose 'this kind of looks like a pattern' read, harmonic patterns require the ratios to actually fit — that precision is the whole point of the approach."},
                    {"heading": "The Gartley pattern", "body": "A bullish Gartley requires (approximately): B retraces 61.8% of XA, C retraces 38.2-88.6% of AB, and D (the entry point) sits at the 78.6% retracement of XA. When the ratios converge near point D, that area is called the PRZ (Potential Reversal Zone) — the anticipated entry."},
                    {"heading": "The Bat pattern", "body": "Similar 5-point structure to the Gartley but with different ratio requirements — most notably, point D sits at a deeper 88.6% retracement of XA (rather than Gartley's 78.6%). Other harmonic patterns (Butterfly, Crab, Shark) each have their own specific ratio signatures — the family shares the X-A-B-C-D skeleton but differs in the precise numbers required at each point."},
                ],
                "notes": [
                    "Harmonic patterns are 5-point (X-A-B-C-D) structures where each leg must fit specific Fibonacci ratios.",
                    "A Gartley's D point sits near 78.6% retracement of XA — the Potential Reversal Zone (PRZ).",
                    "A Bat pattern is similar but with D at a deeper 88.6% retracement of XA.",
                    "Other harmonics (Butterfly, Crab, Shark) share the skeleton but use different ratio requirements.",
                ],
                "quiz": [
                    {"q": "In harmonic pattern trading, the PRZ refers to:", "options": ["The pattern's starting point", "The Potential Reversal Zone where the ratios converge near point D", "A type of moving average"], "answer": 1, "explanation": "The PRZ is where multiple Fibonacci-ratio projections converge near the final (D) point of the pattern, marking the anticipated entry/reversal area."},
                    {"q": "What primarily distinguishes a Gartley pattern from a Bat pattern?", "options": ["The number of points in the structure", "The specific Fibonacci ratio required at point D (78.6% vs. 88.6% of XA)", "Gartley only appears in uptrends"], "answer": 1, "explanation": "Both share the X-A-B-C-D skeleton, but the required retracement depth at D differs — 78.6% for Gartley, 88.6% for Bat."},
                    {"q": "What makes harmonic pattern trading different from a loose visual pattern read?", "options": ["Nothing, they're the same thing", "Each leg must fit specific, precise Fibonacci ratio requirements to qualify", "Harmonic patterns don't use Fibonacci at all"], "answer": 1, "explanation": "The defining feature of the harmonic approach is ratio precision — a shape that merely resembles a Gartley without the correct ratios isn't considered a valid harmonic setup."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Fundamental & Macro Analysis",
        "description": "Trading the news and the bigger economic picture — interest rates, central bank policy, and the high-impact data releases that move currencies fastest.",
        "category": "advanced", "level": "advanced",
        "lessons": [
            {
                "title": "Interest Rates — The Core Driver",
                "summary": "Why interest-rate differentials are the single most important fundamental force in currency valuation.",
                "duration": 9,
                "sections": [
                    {"heading": "Why rates matter so much", "body": "Higher interest rates attract foreign capital seeking better returns on deposits/bonds denominated in that currency — increasing demand for the currency itself. This is the core mechanism behind most major, sustained currency trends; it operates on a longer timescale than most technical setups but tends to dominate the broader direction underneath them."},
                    {"heading": "It's about the DIFFERENTIAL, not the absolute level", "body": "What matters isn't a country's interest rate in isolation, but the DIFFERENTIAL versus other major currencies. A currency with a 4% rate can still weaken if its major counterpart's rate rises to 5.5% — capital flows toward the relatively better return, not just any positive rate."},
                    {"heading": "Rate expectations move markets before the actual decision", "body": "Markets are forward-looking — currencies often move heavily on shifting EXPECTATIONS about future rate decisions (priced in via futures markets, central bank speeches, and economic data), well before the actual rate announcement. By the time a widely-expected rate decision is announced, much of its impact is often already 'priced in,' and the actual reaction can be surprisingly muted — or even move opposite to the raw decision if the guidance/tone differs from expectations."},
                ],
                "notes": [
                    "Higher rates attract foreign capital seeking better returns, generally strengthening a currency.",
                    "What matters is the rate DIFFERENTIAL between currencies, not the absolute rate alone.",
                    "Markets are forward-looking — rate expectations often move price before the actual announcement.",
                    "A widely-expected decision can be 'priced in,' producing a muted or even opposite reaction on the day.",
                ],
                "quiz": [
                    {"q": "Currency strength from interest rates is primarily driven by:", "options": ["The absolute rate level alone", "The rate DIFFERENTIAL relative to other major currencies", "How often the central bank meets"], "answer": 1, "explanation": "Capital flows toward the relatively better return between currencies — what matters is the comparison, not one country's rate in isolation."},
                    {"q": "Why can an announced rate decision sometimes cause a muted or even opposite market reaction?", "options": ["The announcement was fake", "The decision was already 'priced in' by prior expectations, and guidance/tone can differ from the raw number", "Interest rates don't actually affect currencies"], "answer": 1, "explanation": "Forward-looking markets often price in a widely-expected decision beforehand — the actual surprise (or lack of one) is what drives the reaction, not the headline number alone."},
                ],
            },
            {
                "title": "Central Banks & Monetary Policy",
                "summary": "How the Fed, ECB, and other major central banks actually communicate their intentions — and why tone matters as much as action.",
                "duration": 9,
                "sections": [
                    {"heading": "The major players", "body": "Federal Reserve (USD), European Central Bank (EUR), Bank of England (GBP), Bank of Japan (JPY), Reserve Bank of Australia (AUD), Bank of Canada (CAD) — each sets policy independently for their own economy, and the relative divergence/convergence between any two of these drives the corresponding currency pair."},
                    {"heading": "Hawkish vs. dovish", "body": "'Hawkish' language signals a central bank leaning toward higher rates / tighter policy (fighting inflation) — generally currency-positive. 'Dovish' language signals leaning toward lower rates / looser policy (supporting growth/employment) — generally currency-negative. The SAME rate decision can be interpreted very differently depending on the accompanying tone."},
                    {"heading": "Forward guidance", "body": "Central banks routinely signal their LIKELY future path (not just today's decision) through statements, meeting minutes, and press conferences — this is 'forward guidance.' Because markets are forward-looking, guidance about future meetings often moves currencies more than the current decision itself, especially when the current decision was already widely expected."},
                ],
                "notes": [
                    "Major central banks: Fed (USD), ECB (EUR), BoE (GBP), BoJ (JPY), RBA (AUD), BoC (CAD).",
                    "Hawkish = leaning toward tighter policy/higher rates, generally currency-positive.",
                    "Dovish = leaning toward looser policy/lower rates, generally currency-negative.",
                    "Forward guidance about FUTURE meetings often moves markets more than the current decision alone.",
                ],
                "quiz": [
                    {"q": "'Hawkish' central bank language generally signals:", "options": ["Leaning toward lower rates / looser policy", "Leaning toward higher rates / tighter policy — generally currency-positive", "No change in stance at all"], "answer": 1, "explanation": "Hawkish language leans toward tightening (fighting inflation with higher rates), which tends to support the currency."},
                    {"q": "'Forward guidance' refers to:", "options": ["A trading indicator", "A central bank signaling its likely future policy path, not just the current decision", "A type of stop-loss order"], "answer": 1, "explanation": "Because markets price in expectations, guidance about FUTURE decisions can move a currency significantly, sometimes more than the current announcement itself."},
                ],
            },
            {
                "title": "High-Impact Economic Data",
                "summary": "The specific releases that move currencies fastest — NFP, CPI, GDP — and why timing matters as much as the number.",
                "duration": 10,
                "sections": [
                    {"heading": "Non-Farm Payrolls (NFP)", "body": "Released monthly (first Friday, US), NFP measures US job creation excluding farm workers — one of the most consistently market-moving releases in forex, particularly for USD pairs. A significant beat or miss versus consensus forecast can produce sharp, fast moves within seconds of release, often with wide initial spreads and heavy slippage risk."},
                    {"heading": "CPI — inflation data", "body": "Consumer Price Index measures inflation — a core input into central bank rate decisions. Higher-than-expected CPI often raises expectations of future rate hikes (currency-positive, all else equal), while lower-than-expected CPI often does the opposite. Because CPI feeds directly into interest-rate expectations, it's one of the most closely watched data points of any month."},
                    {"heading": "GDP and the 'consensus surprise' principle", "body": "GDP (Gross Domestic Product) measures overall economic growth. Across ALL high-impact data, what actually moves price isn't the raw number — it's the SURPRISE relative to consensus forecast. A 'good' number that comes in exactly as expected often produces little movement; a 'mediocre' number that beats a very low expectation can rally the currency, because markets trade the surprise, not the headline."},
                ],
                "notes": [
                    "NFP (first Friday of the month, US) is one of the most consistently volatile forex releases.",
                    "CPI (inflation) feeds directly into rate expectations — closely watched by every major participant.",
                    "GDP measures overall growth, released quarterly for most major economies.",
                    "What moves price is the SURPRISE vs. consensus forecast, not the raw number alone.",
                ],
                "quiz": [
                    {"q": "What typically causes a sharp currency move on a data release, more than the raw number itself?", "options": ["The exact numerical value alone, regardless of expectations", "The SURPRISE — how the actual figure compares to the consensus forecast", "The day of the week it's released"], "answer": 1, "explanation": "A number matching expectations tends to be already priced in; the actual market-moving element is how far the outcome diverges from what was expected."},
                    {"q": "Higher-than-expected CPI (inflation) data generally leads markets to expect:", "options": ["Lower future interest rates", "Higher future interest rates, often currency-positive", "No change in central bank thinking"], "answer": 1, "explanation": "Since fighting inflation is a core central bank mandate, hotter inflation data often raises the odds of future tightening — generally supportive for the currency."},
                    {"q": "Non-Farm Payrolls (NFP) is significant mainly because:", "options": ["It's released daily", "It's one of the most consistently market-moving US data releases, especially for USD pairs", "It measures GDP directly"], "answer": 1, "explanation": "As a key US labor-market gauge released monthly, NFP surprises regularly produce some of the sharpest short-term forex moves, particularly across USD pairs."},
                ],
            },
            {
                "title": "Trading Around News Events",
                "summary": "The practical risks of trading through high-impact releases, and the approaches serious traders use to manage them.",
                "duration": 8,
                "sections": [
                    {"heading": "Why news events are uniquely risky", "body": "During major releases, spreads can widen dramatically (sometimes 5-10x normal), slippage on stop-losses can be severe, and price can whipsaw violently in both directions within seconds before settling on a real direction. A perfectly-sized position under normal conditions can end up with a much larger effective loss than planned if a stop gets filled well past its intended price during the volatility spike."},
                    {"heading": "Common approaches", "body": "Avoid entering NEW trades in the minutes immediately before a high-impact release — the risk/reward of guessing direction pre-release is generally poor. For existing positions, some traders reduce size or tighten stops ahead of known releases; others widen stops to avoid being needlessly whipsawed out by the initial spike, accepting more risk per trade in exchange for staying in a position they still believe in."},
                    {"heading": "Trading the aftermath, not the spike", "body": "A more conservative, commonly used approach: wait for the initial volatile spike to settle (often just a few minutes), then trade the resulting clearer directional move with normal spreads and more predictable execution — accepting a later, sometimes smaller entry in exchange for meaningfully lower execution risk."},
                ],
                "notes": [
                    "Spreads and slippage risk can spike dramatically (5-10x normal) during high-impact releases.",
                    "Guessing direction with a new trade right before a release generally has poor risk/reward.",
                    "Some traders adjust size/stops ahead of known releases rather than avoiding them entirely.",
                    "A common conservative approach: wait for the initial spike to settle, then trade the clearer aftermath.",
                ],
                "quiz": [
                    {"q": "During a high-impact news release, spreads and slippage risk typically:", "options": ["Stay exactly the same as normal conditions", "Widen/increase significantly, sometimes 5-10x normal", "Disappear entirely"], "answer": 1, "explanation": "The sudden volatility and reduced orderly liquidity around major releases commonly causes much wider spreads and greater slippage risk than typical conditions."},
                    {"q": "A conservative approach to trading news events is to:", "options": ["Always enter a new trade right at the exact release moment", "Wait for the initial volatile spike to settle, then trade the clearer resulting move", "Never trade on release days at all, under any circumstances"], "answer": 1, "explanation": "This approach trades away some potential early profit in exchange for meaningfully more predictable spreads and execution once the initial chaos settles."},
                ],
            },
        ],
    },
    # ────────────────────────────────────────────────────────────────────────
    {
        "title": "Building a Professional Trading Plan",
        "description": "Turning everything else in this hub into one coherent, written system — the document that actually separates consistent traders from everyone else.",
        "category": "advanced", "level": "advanced",
        "lessons": [
            {
                "title": "Why a Written Plan Changes Everything",
                "summary": "The specific failure mode a trading plan is designed to prevent — and why 'I know my strategy' isn't the same as having one.",
                "duration": 6,
                "sections": [
                    {"heading": "The gap between knowing and doing", "body": "Most traders can correctly EXPLAIN good risk management, entry criteria, and discipline in the abstract. Very few consistently EXECUTE those same principles in the heat of a live, emotionally-charged trade. A written plan exists specifically to close that gap — it's a commitment made by your calm, analytical self, binding on your in-the-moment, emotional self."},
                    {"heading": "What a real plan actually contains", "body": "Not a vague mission statement — a real trading plan specifies, concretely: which setups you take (and, just as importantly, which you don't), which pairs and timeframes, your exact risk-per-trade rule, your minimum acceptable R:R, your trading hours/sessions, and your rules for after a loss or a losing streak."},
                    {"heading": "Treat it as a living document — with discipline about WHEN it changes", "body": "A plan should evolve as you learn — but changes belong between trading sessions, based on journal review over many trades, never mid-trade or mid-losing-streak. Changing your rules in reaction to a single bad trade is exactly the emotional decision-making the plan exists to prevent."},
                ],
                "notes": [
                    "A plan exists to bind your in-the-moment emotional self to decisions made by your calm, analytical self.",
                    "It should specify setups, pairs, timeframes, risk%, minimum R:R, hours, and post-loss rules concretely.",
                    "Treat it as a living document — but change it between sessions based on journal review, never mid-trade.",
                    "Changing rules in reaction to one bad trade defeats the entire purpose of having a plan.",
                ],
                "quiz": [
                    {"q": "The core purpose of a written trading plan is to:", "options": ["Guarantee profitable trades", "Bind your in-the-moment emotional decisions to the rules your calm, analytical self decided in advance", "Satisfy a regulatory requirement"], "answer": 1, "explanation": "The plan's value is precommitment — removing the need to make good decisions while emotionally invested in an open trade."},
                    {"q": "When should a trading plan's rules be revised?", "options": ["Immediately after any single losing trade", "Between sessions, based on journal review across many trades", "Never — it should stay fixed forever"], "answer": 1, "explanation": "Reacting to one trade is exactly the emotional decision-making the plan is meant to prevent; real revisions should come from patterns visible across many logged trades."},
                ],
            },
            {
                "title": "Defining Your Edge & Setups",
                "summary": "Writing down exactly what a valid setup looks like, so 'good enough' stops being a feeling and starts being a checklist.",
                "duration": 8,
                "sections": [
                    {"heading": "What is an 'edge', specifically", "body": "Your edge is the specific, repeatable condition (or combination of conditions) under which you have a statistical advantage — e.g., 'a pin bar rejection at a daily S/R zone, aligned with the H4 trend, with RSI confirming momentum.' A vague edge like 'good-looking setups' isn't testable, reviewable, or improvable."},
                    {"heading": "Writing setup criteria as a checklist", "body": "Convert your edge into a literal checklist: specific conditions that must ALL be true before you take the trade. This does two things — it filters out marginal, half-qualifying setups you'd otherwise talk yourself into, and it makes your journal reviewable (you can actually check whether losing trades followed the checklist or skipped steps)."},
                    {"heading": "One primary setup beats five vague ones", "body": "Beginners often try to trade many different setup types simultaneously, mastering none of them. A narrower, well-defined, and thoroughly practiced single setup (or two) tends to outperform a wide net of loosely-defined ones — depth of understanding on a smaller number of patterns beats shallow familiarity with many."},
                ],
                "notes": [
                    "An 'edge' should be specific and repeatable, not a vague feeling of 'good-looking setups'.",
                    "Convert setup criteria into a literal checklist — all conditions must be true before entry.",
                    "A checklist makes journal review meaningful — you can check if losses skipped a step.",
                    "One or two well-defined, deeply practiced setups tend to beat many loosely-defined ones.",
                ],
                "quiz": [
                    {"q": "A well-defined trading 'edge' should be:", "options": ["A general feeling about good opportunities", "Specific and repeatable, testable against a checklist", "Different every single trade"], "answer": 1, "explanation": "Vague criteria can't be reviewed, tested, or improved — a specific repeatable definition is what actually makes a setup analyzable over time."},
                    {"q": "Beginners trying to master many different setup types at once typically:", "options": ["Improve faster than focusing on one or two", "Develop shallower understanding of each, often underperforming a narrower focus", "Have no disadvantage compared to specializing"], "answer": 1, "explanation": "Depth of understanding and repetition on a smaller, well-defined set of setups tends to build real skill faster than spreading attention thin."},
                ],
            },
            {
                "title": "Setting Rules for Losing Streaks",
                "summary": "Deciding, in advance, exactly what happens after 2, 5, and 10 consecutive losses — before you're actually in that situation.",
                "duration": 7,
                "sections": [
                    {"heading": "Why this needs to be decided in advance", "body": "During an actual losing streak, judgment is exactly at its weakest — the tilt/revenge-trading dynamics covered elsewhere in this hub are strongest precisely when you'd otherwise be deciding 'what to do next.' Pre-deciding removes that decision from the worst possible moment to make it."},
                    {"heading": "A tiered response", "body": "A common structure: after 2-3 consecutive losses, pause and review (not necessarily stop entirely, but slow down and re-check process). After 5 consecutive losses, or hitting a daily loss limit (e.g. 6% of account), stop trading for the day entirely. After a larger drawdown threshold (e.g. 15-20% from peak), stop trading altogether and do a full strategy/execution review before resuming."},
                    {"heading": "Distinguishing normal variance from a broken system", "body": "Losing streaks happen to sound strategies too — that's normal variance, not proof something is wrong. The tiered rules aren't about assuming failure after every streak; they're about creating a mandatory PAUSE POINT for objective review, so a genuine problem (if one exists) gets caught before it compounds, rather than being emotionally powered through."},
                ],
                "notes": [
                    "Decide loss-streak rules in advance — judgment is weakest exactly when you'd need to decide in the moment.",
                    "Common tiers: pause/review after 2-3 losses, stop for the day after 5 or a daily loss limit, full review after a larger drawdown.",
                    "Losing streaks happen to sound strategies too — the rules exist to create a mandatory check, not assume failure.",
                    "The goal is catching a genuine problem early, not powering through emotionally.",
                ],
                "quiz": [
                    {"q": "Why should loss-streak rules be decided in advance rather than in the moment?", "options": ["It doesn't matter when they're decided", "Judgment tends to be weakest exactly during a losing streak — pre-deciding avoids relying on it then", "Rules decided in the moment are always better calibrated"], "answer": 1, "explanation": "This mirrors the tilt/revenge-trading pattern — deciding while calm avoids needing good judgment exactly when it's least reliable."},
                    {"q": "A losing streak happening to a sound, well-tested strategy is:", "options": ["Proof the strategy is broken and should be abandoned immediately", "Normal statistical variance — the pause rules exist for review, not automatic failure assumption", "Impossible if the strategy has positive expectancy"], "answer": 1, "explanation": "Even genuinely profitable strategies experience losing streaks as part of normal variance — the tiered rules create a checkpoint, not an automatic verdict."},
                ],
            },
            {
                "title": "Reviewing & Iterating Your Plan",
                "summary": "Turning your trading journal into an actual feedback loop that improves the plan itself over time.",
                "duration": 7,
                "sections": [
                    {"heading": "What to actually review", "body": "Beyond simple win/loss counts: which specific setup types perform best/worst for you personally, which sessions/times of day correlate with your better or worse decisions, how often you actually followed your own checklist versus deviated, and whether your real average R:R matches what your plan assumes."},
                    {"heading": "A monthly review cadence", "body": "Weekly reviews catch short-term drift (are you still following the checklist?); monthly reviews are better suited to spotting real PATTERNS across enough trades to be statistically meaningful — a single week rarely has enough sample size to draw a confident conclusion about a specific setup's real performance."},
                    {"heading": "Iterating without overreacting", "body": "The goal of review is gradual, evidence-based refinement — tightening a criterion that's shown to correlate with losses, dropping a setup type that consistently underperforms, adjusting session hours that produce worse decisions — not a wholesale rewrite of the plan after every rough patch. A plan that changes completely every month was never really being tested in the first place."},
                ],
                "notes": [
                    "Review setup-by-setup performance, time-of-day patterns, checklist adherence, and real vs. assumed R:R.",
                    "Weekly reviews catch short-term drift; monthly reviews are better for spotting real statistical patterns.",
                    "Iterate gradually based on evidence — don't rewrite the whole plan after every rough patch.",
                    "A plan changing completely every month was never actually being tested.",
                ],
                "quiz": [
                    {"q": "Monthly reviews (versus weekly) are especially useful for:", "options": ["Catching what you had for breakfast", "Spotting real statistical patterns across a large enough sample of trades", "Replacing the need for weekly reviews entirely"], "answer": 1, "explanation": "A single week rarely contains enough trades to draw a statistically confident conclusion about a specific setup or pattern — a month gives a larger, more meaningful sample."},
                    {"q": "The recommended approach to iterating a trading plan is:", "options": ["A complete rewrite after every losing week", "Gradual, evidence-based refinement based on patterns across many trades", "Never changing it once written"], "answer": 1, "explanation": "Small, evidence-driven adjustments preserve the ability to actually test whether a change helped — constant wholesale rewrites make that impossible to evaluate."},
                ],
            },
        ],
    },
]
