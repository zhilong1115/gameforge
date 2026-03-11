# HU — Roguelike Mahjong Deck-Builder

## Concept
A single-player roguelike where you play mahjong hands to clear score targets. Between rounds, buy god tiles (passive abilities) and flower cards (consumables) from a shop. Inspired by Balatro but with Chinese mahjong.

## Core Mechanics

### Tiles
- 136 tiles: 3 number suits (万/条/筒, values 1-9, 4 copies each) + 4 winds + 3 dragons
- Materials: tiles can have special materials (gold, jade, ice, etc.) with bonus effects

### Winning a Hand
- 14 tiles = 4 melds (chow/pong/kong) + 1 pair
- Win forms: Standard (4+1), Seven Pairs, Thirteen Orphans
- Player starts with 14 tiles, 5 discard budget

### Scoring
```
finalScore = (baseScore + chipModifiers) × (fanMultiplier × multMultiplier)
baseScore = 50
```

### Fan Patterns (Multipliers)
- Basic: 平和 ×1, 一气通贯 ×2
- Mid: 混一色 ×3, 对对和 ×5, 七对 ×6
- High: 清一色 ×8, 大三元 ×16
- Yakuman: 国士无双 ×88

### Roguelike Structure
- 8 Antes, each with 3 Blinds (Small → Big → Boss)
- Target scores scale from 300 (Ante 1) to 2700+ (Ante 8)
- Between blinds: shop phase

### God Tiles (28 total)
Passive abilities, 4 bonds × 7 tiles:
- 🎲 Gamble: high risk / high reward probability effects
- 👁️ Vision: card visibility and information advantages
- 💰 Wealth: gold generation and economy scaling
- 🔄 Transform: tile manipulation and material bonuses

Bond levels at 2/4/6 tiles provide escalating passive bonuses.

### Flower Cards (32 total)
Consumables, 4 types × 8 cards:
- 🌸 Plum, 🎋 Bamboo, 🌺 Orchid, 🏵️ Chrysanthemum

### Economy
- Earn gold for clearing blinds
- Spend gold in shop on god tiles and flower cards
- Starting gold: 4

## Target Platform
- YouTube Playables (HTML5, <5MB, mobile-first, portrait 9:16)

## Tech Stack
- Engine: Phaser 3
- Language: TypeScript
- Build: Vite

## Balance Targets
- Ante 1-2 win rate: 65-80% (learnable)
- Ante 3-5 win rate: 45-60% (strategic)
- Ante 6-8 win rate: 25-45% (mastery)
- 4+ viable build strategies
- No single god tile with >90% purchase rate
