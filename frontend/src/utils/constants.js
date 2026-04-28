export const METRIC_LABELS = {
  ORtg: 'Off Rating',
  DRtg: 'Def Rating',
  NET_RTG: 'Net Rating',
  PACE: 'Pace',
  PPG: 'Points/G',
  eFG: 'eFG%',
  TS: 'TS%',
  AST_RATE: 'Ast%',
  TOV_RATE: 'TOV%',
  'Opp_TOV%': 'Opp TOV%',
  GP: 'GP',
  TEAM_ABBREVIATION: 'Team',
};

// Metrics where lower value = better
export const ASC_METRICS = new Set(['DRtg', 'TOV_RATE', 'Opp_TOV%']);

// All queryable metrics in display order
export const ALL_METRICS = [
  'NET_RTG',
  'ORtg',
  'DRtg',
  'PACE',
  'PPG',
  'eFG',
  'TS',
  'AST_RATE',
  'TOV_RATE',
  'Opp_TOV%',
];

export const WINDOWS = ['SEASON', 'LAST_5', 'LAST_10', 'LAST_20'];

export const SEASON_TYPES = ['Regular Season', 'Playoffs'];

export const SEASON_TYPE_LABELS = {
  'Regular Season': 'Regular Season',
  Playoffs: 'Playoffs',
};

export const WINDOW_LABELS = {
  SEASON: 'Full Season',
  LAST_5: 'Last 5 Games',
  LAST_10: 'Last 10 Games',
  LAST_20: 'Last 20 Games',
};

export const COMPARE_METRICS_DEFAULT = ['NET_RTG', 'ORtg', 'DRtg', 'PACE', 'eFG', 'TS'];

export const NBA_TEAMS = [
  'ATL', 'BOS', 'BKN', 'CHA', 'CHI',
  'CLE', 'DAL', 'DEN', 'DET', 'GSW',
  'HOU', 'IND', 'LAC', 'LAL', 'MEM',
  'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
  'OKC', 'ORL', 'PHI', 'PHX', 'POR',
  'SAC', 'SAS', 'TOR', 'UTA', 'WAS',
];

export const TEAM_NAMES = {
  ATL: 'Atlanta Hawks',
  BOS: 'Boston Celtics',
  BKN: 'Brooklyn Nets',
  CHA: 'Charlotte Hornets',
  CHI: 'Chicago Bulls',
  CLE: 'Cleveland Cavaliers',
  DAL: 'Dallas Mavericks',
  DEN: 'Denver Nuggets',
  DET: 'Detroit Pistons',
  GSW: 'Golden State Warriors',
  HOU: 'Houston Rockets',
  IND: 'Indiana Pacers',
  LAC: 'LA Clippers',
  LAL: 'LA Lakers',
  MEM: 'Memphis Grizzlies',
  MIA: 'Miami Heat',
  MIL: 'Milwaukee Bucks',
  MIN: 'Minnesota Timberwolves',
  NOP: 'New Orleans Pelicans',
  NYK: 'New York Knicks',
  OKC: 'Oklahoma City Thunder',
  ORL: 'Orlando Magic',
  PHI: 'Philadelphia 76ers',
  PHX: 'Phoenix Suns',
  POR: 'Portland Trail Blazers',
  SAC: 'Sacramento Kings',
  SAS: 'San Antonio Spurs',
  TOR: 'Toronto Raptors',
  UTA: 'Utah Jazz',
  WAS: 'Washington Wizards',
};

export const EXAMPLE_QUERIES = [
  'Show the top 10 teams by net rating this season',
  'Which teams have the best offense in the last 10 games?',
  'Compare the Celtics and Lakers on offense and defense',
  'Show offensive vs defensive ratings for all teams',
  'Worst 5 defensive teams over the last 20 games',
  'Who leads the league in pace this season?',
];
