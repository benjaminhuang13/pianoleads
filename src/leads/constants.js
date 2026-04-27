export const LEAD_STATUS = ['new', 'contacted', 'qualified', 'closed', 'taken'];

export const SOURCE_TYPE = [
  'google_maps', 'google_search', 'rcm', 'mtna', 'conservatory',
  'youtube', 'facebook', 'instagram', 'thumbtack', 'yelp',
  'domain_crawl', 'manual',
];

export const TERRITORY = ['nyc_metro', 'long_island', 'north_jersey'];

export const READ_ONLY = new Set([
  'id', 'google_place_id', 'rating', 'review_count',
  'most_recent_review', 'photo_count', 'found_at', 'updated_at',
]);
