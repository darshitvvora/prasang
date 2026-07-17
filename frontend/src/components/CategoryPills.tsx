import type { ArtistType } from '../types/artist';
import './CategoryPills.css';

interface CategoryPillsProps {
  activeCategory: ArtistType | 'all';
  onCategoryChange: (category: ArtistType | 'all') => void;
}

const categories: { key: ArtistType | 'all'; label: string; icon: string }[] = [
  { key: 'all', label: 'All Artists', icon: '✨' },
  { key: 'magician', label: 'Magician', icon: '🎩' },
  { key: 'dj', label: 'DJ', icon: '🎧' },
  { key: 'singer', label: 'Singer', icon: '🎤' },
  { key: 'comedian', label: 'Comedian', icon: '😂' },
  { key: 'band', label: 'Band', icon: '🎸' },
  { key: 'anchor', label: 'Anchor', icon: '🎙️' },
  { key: 'bubble_artist', label: 'Bubble Artist', icon: '🫧' },
  { key: 'body_double', label: 'Body Double', icon: '🎭' },
];

export default function CategoryPills({ activeCategory, onCategoryChange }: CategoryPillsProps) {
  return (
    <section className="category-pills-section" id="category-pills">
      <div className="container">
        <div className="category-pills-header">
          <h2 className="category-pills-title">Discover Artists</h2>
          <p className="category-pills-subtitle">Browse by category or search for your perfect match</p>
        </div>
        <div className="category-pills-wrapper" role="tablist" aria-label="Artist categories">
          {categories.map((cat) => (
            <button
              key={cat.key}
              type="button"
              role="tab"
              aria-selected={activeCategory === cat.key}
              className={`category-pill${activeCategory === cat.key ? ' active' : ''}`}
              onClick={() => onCategoryChange(cat.key)}
            >
              <span className="category-pill-icon" aria-hidden="true">{cat.icon}</span>
              {cat.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
