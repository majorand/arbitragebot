/**
 * Sport, league, market, and matchup registry
 */

const SPORTS = {
  nfl: {
    name: 'NFL',
    markets: ['ML', 'Spread', 'Props', '1H ML', '1Q ML'],
    teams: [
      ['Chiefs', 'Bills'], ['Eagles', 'Cowboys'], ['49ers', 'Rams'],
      ['Ravens', 'Bengals'], ['Lions', 'Packers'], ['Dolphins', 'Jets'],
      ['Texans', 'Jaguars'], ['Bears', 'Vikings'], ['Steelers', 'Browns'],
      ['Seahawks', 'Cardinals'], ['Chargers', 'Raiders'], ['Broncos', 'Titans'],
      ['Falcons', 'Saints'], ['Panthers', 'Buccaneers'], ['Commanders', 'Giants'],
    ],
  },
  nba: {
    name: 'NBA',
    markets: ['ML', 'Spread', 'Props', '1H ML', '1Q Spread'],
    teams: [
      ['Lakers', 'Celtics'], ['Warriors', 'Nuggets'], ['Bucks', 'Heat'],
      ['76ers', 'Knicks'], ['Suns', 'Mavericks'], ['Grizzlies', 'Pelicans'],
      ['Cavaliers', 'Pacers'], ['Thunder', 'Timberwolves'], ['Kings', 'Clippers'],
      ['Hawks', 'Bulls'], ['Nets', 'Raptors'], ['Spurs', 'Rockets'],
      ['Jazz', 'Trail Blazers'], ['Magic', 'Pistons'], ['Hornets', 'Wizards'],
    ],
  },
  mlb: {
    name: 'MLB',
    markets: ['ML', 'Spread', '1H ML', 'Props'],
    teams: [
      ['Yankees', 'Red Sox'], ['Dodgers', 'Giants'], ['Astros', 'Rangers'],
      ['Braves', 'Phillies'], ['Mets', 'Cubs'], ['Padres', 'Diamondbacks'],
      ['Orioles', 'Blue Jays'], ['Twins', 'Guardians'], ['Mariners', 'Angels'],
      ['Cardinals', 'Brewers'], ['Rays', 'Tigers'], ['White Sox', 'Royals'],
    ],
  },
  nhl: {
    name: 'NHL',
    markets: ['ML', 'Spread', '1Q Spread'],
    teams: [
      ['Oilers', 'Flames'], ['Maple Leafs', 'Canadiens'], ['Rangers', 'Islanders'],
      ['Bruins', 'Penguins'], ['Lightning', 'Panthers'], ['Avalanche', 'Stars'],
      ['Golden Knights', 'Kings'], ['Hurricanes', 'Devils'], ['Capitals', 'Flyers'],
      ['Jets', 'Wild'], ['Canucks', 'Kraken'], ['Blues', 'Predators'],
    ],
  },
  epl: {
    name: 'EPL',
    markets: ['ML', 'Spread', 'Props', 'Live ML'],
    teams: [
      ['Arsenal', 'Man City'], ['Liverpool', 'Chelsea'], ['Man Utd', 'Tottenham'],
      ['Newcastle', 'Aston Villa'], ['Brighton', 'West Ham'], ['Brentford', 'Fulham'],
      ['Wolves', 'Crystal Palace'], ['Everton', 'Bournemouth'], ['Forest', 'Leicester'],
    ],
  },
  la_liga: {
    name: 'La Liga',
    markets: ['ML', 'Spread', '1Q Spread'],
    teams: [
      ['Barcelona', 'Real Madrid'], ['Atletico', 'Sevilla'], ['Villarreal', 'Real Sociedad'],
      ['Real Betis', 'Athletic Club'], ['Valencia', 'Girona'], ['Celta Vigo', 'Osasuna'],
    ],
  },
  ufc: {
    name: 'UFC',
    markets: ['ML', 'Spread'],
    teams: [
      ['Jones', 'Aspinall'], ['Adesanya', 'Pereira'], ['Makhachev', 'Oliveira'],
      ['Volkanovski', 'Topuria'], ['Edwards', 'Muhammad'], ['Dvalishvili', 'O\'Malley'],
      ['Pantoja', 'Moreno'], ['Grasso', 'Shevchenko'], ['Du Plessis', 'Strickland'],
    ],
  },
  tennis: {
    name: 'Tennis',
    markets: ['ML', 'Spread', 'Props'],
    teams: [
      ['Djokovic', 'Alcaraz'], ['Sinner', 'Medvedev'], ['Rune', 'Fritz'],
      ['Tsitsipas', 'Zverev'], ['Ruud', 'Rublev'], ['Swiatek', 'Sabalenka'],
      ['Gauff', 'Rybakina'], ['de Minaur', 'Shelton'], ['Draper', 'Tiafoe'],
    ],
  },
};

/**
 * Get a random matchup for a given sport
 */
function getRandomMatchup(sportKey) {
  const sport = SPORTS[sportKey];
  if (!sport) return null;

  const teams = sport.teams[Math.floor(Math.random() * sport.teams.length)];
  const market = sport.markets[Math.floor(Math.random() * sport.markets.length)];

  return {
    league: sport.name,
    teamA: teams[0],
    teamB: teams[1],
    market,
  };
}

/**
 * Get all active sport keys from a sports flag
 */
function parseSportsFlag(flag) {
  if (flag === 'all') return Object.keys(SPORTS);
  return flag.split(',').map(s => s.trim().toLowerCase()).filter(s => s in SPORTS);
}

module.exports = {
  SPORTS,
  getRandomMatchup,
  parseSportsFlag,
};
