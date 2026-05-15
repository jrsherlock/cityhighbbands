import { defineCollection, z } from 'astro:content';

const ensembles = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),
    category: z.enum(['concert', 'marching', 'jazz']),
    conductors: z.array(z.string()).default([]),
    summary: z.string().default(''),
    hero_image: z.string().default(''),
  }),
});

const piece = z.object({
  title: z.string(),
  composer: z.string().default(''),
  arranger: z.string().default(''),
  year: z.string().default(''),
  note: z.string().default(''),
});

const programs = defineCollection({
  type: 'content',
  schema: z.object({
    ensemble_slug: z.string(),
    event_name: z.string(),
    venue: z.string().default(''),
    date_raw: z.string().default(''),
    date_iso: z.string().default(''),
    season: z.string().default(''),
    program_title: z.string().default(''),
    pieces: z.array(piece).default([]),
    flags: z.array(z.string()).default([]),
  }),
});

const member = z.object({
  name: z.string(),
  grade: z.string().default(''),
  instrument: z.string().default(''),
  note: z.string().default(''),
});

const seasons = defineCollection({
  type: 'content',
  schema: z.object({
    year_range: z.string(),
    start_year: z.number(),
    marching: z.record(z.any()).default({}),
    ensembles: z.record(z.array(z.string())).default({}),
    all_state: z.array(member).default([]),
    seiba: z.array(member).default([]),
    uni_honor: z.array(member).default([]),
    iowa_honor: z.array(member).default([]),
    all_state_jazz: z.array(member).default([]),
    awards: z.array(z.object({
      category: z.string(),
      recipients: z.array(z.string()).default([]),
    })).default([]),
    body_raw: z.string().default(''),
  }),
});

const directors = defineCollection({
  type: 'content',
  schema: z.object({
    name: z.string(),
    role: z.string().default(''),
    photo: z.string().default(''),
    email: z.string().default(''),
  }),
});

const pages = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    breadcrumb: z.array(z.string()).default([]),
    source_url: z.string().default(''),
    hero: z.string().default(''),
  }),
});

const events = defineCollection({
  type: 'data',
  schema: z.object({
    title: z.string(),
    program_title: z.string().default(''),
    date: z.string(),                 // YYYY-MM-DD
    time: z.string().default(''),     // "7:00 PM"
    end_time: z.string().default(''),
    venue: z.string().default(''),
    ensemble_slug: z.string().default(''),
    ensemble_label: z.string().default(''),
    note: z.string().default(''),
    free: z.boolean().default(true),
  }),
});

export const collections = { ensembles, programs, seasons, directors, pages, events };
