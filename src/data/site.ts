/**
 * Single source of truth for site-wide identity, navigation and the
 * category (information architecture) model.
 *
 * The category list is deliberately fixed and small: every published article
 * must belong to exactly one of these hubs, which keeps the internal linking
 * graph shallow (Home -> Category -> Article) and crawlable.
 */

export const SITE = {
  name: "The Owner's Handbook",
  shortName: 'Owner Handbook',
  domain: 'ownerhandbook.com',
  url: 'https://ownerhandbook.com',
  locale: 'en-US',
  lang: 'en',
  tagline: 'Practical startup and operations guides for small business owners',
  description:
    "The Owner's Handbook publishes step-by-step guides for starting and running a small business in the United States: startup costs, licensing and registration, pricing, tools and getting customers. Every guide cites primary sources — state agencies, the SBA, the IRS and published vendor pricing.",
  publisher: "The Owner's Handbook",
  // Contact address is shown on the Contact page and used in Organization schema.
  // Swap for a domain-backed mailbox once the domain is live.
  contactEmail: 'hello@ownerhandbook.com',
  founded: '2026',
  // Social profiles: add once created; empty strings are filtered out of JSON-LD.
  social: {
    x: '',
    linkedin: '',
    facebook: '',
  },
} as const;

export type CategorySlug =
  | 'start-a-business'
  | 'startup-costs'
  | 'licensing-and-registration'
  | 'pricing'
  | 'tools-and-software'
  | 'getting-customers';

export interface Category {
  slug: CategorySlug;
  name: string;
  /** One-line label used in nav/menus. */
  short: string;
  /** Meta description + category page intro. Written for search intent. */
  description: string;
  /** The question this hub answers — used in the category page H1 support copy. */
  intent: string;
  /** Seed cluster from the Phase 0 niches research (Phase 2 publishes these). */
  planned: string[];
}

export const CATEGORIES: Category[] = [
  {
    slug: 'start-a-business',
    name: 'Starting a Business',
    short: 'Starting a Business',
    description:
      'Industry-by-industry guides to launching a small business in the US: what the work actually involves, what you need before your first customer, and the order to do it in.',
    intent: 'How do I start this specific type of business, step by step?',
    planned: [
      'How to Start a Cleaning Business',
      'How to Start a Pressure Washing Business',
      'How to Start a Landscaping Business',
      'How to Start a Painting Business',
      'How to Start a Handyman Business',
      'How to Start a Pet Grooming Business',
      'How to Start a Daycare',
      'How to Start a Trucking Business',
      'How to Start a Food Truck Business',
      'How to Start a Home Inspection Business',
      'How to Start a Mobile Detailing Business',
      'How to Start an Event Planning Business',
    ],
  },
  {
    slug: 'startup-costs',
    name: 'Startup Costs',
    short: 'Startup Costs',
    description:
      'Line-item startup and operating cost breakdowns for small businesses, built from published equipment prices, insurance quotes and licensing fees — not estimates pulled out of thin air.',
    intent: 'What will this business actually cost me to start and run?',
    planned: [
      'Cleaning Business Startup Costs',
      'Pressure Washing Business Startup Costs',
      'Landscaping Business Startup Costs',
      'Trucking Business Startup Costs',
      'Food Truck Startup Costs',
      'Daycare Startup Costs',
      'How Much Does an LLC Cost by State',
      'Small Business Insurance Cost',
    ],
  },
  {
    slug: 'licensing-and-registration',
    name: 'Licensing & Registration',
    short: 'Licensing & Registration',
    description:
      'The paperwork side of starting a business: entity formation, EINs, state and local licenses, permits and renewals, with links to the agency pages that hold the authoritative requirements.',
    intent: 'What licenses, permits and registrations do I legally need?',
    planned: [
      'How to Get an EIN',
      'Business Licenses by State',
      'Do You Need a License to Start a Cleaning Business',
      'Sole Proprietor vs LLC',
      'Registered Agent: What It Is and What It Costs',
    ],
  },
  {
    slug: 'pricing',
    name: 'Pricing Your Services',
    short: 'Pricing',
    description:
      'How to set and raise prices for service businesses: job costing, hourly versus flat-rate pricing, market rate research and the contracts that keep quotes enforceable.',
    intent: 'How should I price what I sell so the business is profitable?',
    planned: [
      'How to Price Cleaning Services',
      'How to Price Landscaping Jobs',
      'Hourly vs Flat Rate Pricing',
      'How to Write an Estimate That Gets Approved',
    ],
  },
  {
    slug: 'tools-and-software',
    name: 'Tools & Software',
    short: 'Tools & Software',
    description:
      'Software and tool comparisons for owner-operators — scheduling, invoicing, accounting, payments and field apps — evaluated on published pricing and what a one- or two-person shop actually needs.',
    intent: 'Which tools should I buy, and what do they cost at my size?',
    planned: [
      'Best Invoicing Software for Small Business',
      'Best Scheduling Software for Cleaning Businesses',
      'Best Accounting Software for Sole Proprietors',
      'Business Payment Processing Fees Compared',
    ],
  },
  {
    slug: 'getting-customers',
    name: 'Getting Customers',
    short: 'Getting Customers',
    description:
      'Practical customer acquisition for local and service businesses: local SEO, Google Business Profile, reviews, repeat business, referrals and plain-spoken marketing that fits a working owner\'s schedule.',
    intent: 'How do I get my first customers and keep the schedule full?',
    planned: [
      'Local SEO Checklist for Service Businesses',
      'How to Get Google Reviews',
      'How to Get Your First 10 Customers',
      'Referral Programs for Service Businesses',
    ],
  },
];

export const CATEGORY_BY_SLUG: Record<string, Category> = Object.fromEntries(
  CATEGORIES.map((c) => [c.slug, c]),
);

/** Top-level navigation. Kept short — crawl depth stays at two clicks. */
export const NAV = [
  { label: 'Start a Business', href: '/categories/start-a-business/' },
  { label: 'Startup Costs', href: '/categories/startup-costs/' },
  { label: 'Licensing', href: '/categories/licensing-and-registration/' },
  { label: 'Pricing', href: '/categories/pricing/' },
  { label: 'Tools', href: '/categories/tools-and-software/' },
  { label: 'Getting Customers', href: '/categories/getting-customers/' },
] as const;

/** Site-wide legal/policy pages, linked in the footer on every page. */
export const FOOTER_LINKS = [
  { label: 'About', href: '/about/' },
  { label: 'Contact', href: '/contact/' },
  { label: 'Privacy Policy', href: '/privacy-policy/' },
  { label: 'Editorial Policy', href: '/editorial-policy/' },
  { label: 'All Guides', href: '/articles/' },
] as const;

export const absoluteUrl = (path: string): string =>
  new URL(path, SITE.url).toString();
