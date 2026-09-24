export interface Citation {
  n: number;
  text: string;
  url: string;
  publisher: string;
  year: string;
}

export type Block =
  | { kind: 'p'; text: string }
  | { kind: 'lead'; text: string }
  | { kind: 'h3'; text: string }
  | { kind: 'list'; ordered?: boolean; items: string[] }
  | { kind: 'equation'; latex: string; ascii: string; caption?: string }
  | { kind: 'callout'; title: string; text: string; tone?: 'note' | 'caution' }
  | { kind: 'quote'; text: string; attribution?: string }
  | { kind: 'table'; head: string[]; rows: string[][]; caption?: string }
  /** Renders the live, interactive model inline in the reading column. */
  | { kind: 'figure'; figure: 'figure1' | 'figure2'; title: string; caption: string }
  | { kind: 'link'; to: string; label: string; sublabel?: string };

export interface Section {
  id: string;
  navLabel: string;
  title: string;
  blocks: Block[];
}

export interface Paper {
  slug: string;
  title: string;
  subtitle: string;
  author: string;
  affiliation: string;
  date: string;
  readingMinutes: number;
  category: string;
  tags: string[];
  abstract: string;
  question: string;
  sections: Section[];
  citations: Citation[];
}
