import { ArrowRight, Sparkles } from 'lucide-react';
import type { Artist } from '../types/artist';
import ArtistCard from './ArtistCard';
import './ArtistGrid.css';

interface ArtistGridProps {
  artists: Artist[];
}

export default function ArtistGrid({ artists }: ArtistGridProps) {
  // Insert "Show All" card at position 3 (after 3 cards)
  const firstThree = artists.slice(0, 3);
  const rest = artists.slice(3);

  return (
    <section className="artist-grid-section" id="artist-grid">
      <div className="container">
        <div className="artist-grid">
          {firstThree.map((artist) => (
            <ArtistCard key={artist.artistId} artist={artist} />
          ))}

          {/* Show All Card */}
          <div className="artist-grid-show-all" role="link" tabIndex={0} id="show-all-artists">
            <div className="artist-grid-show-all-arrow">
              <ArrowRight size={24} />
            </div>
            <div className="artist-grid-show-all-title">Show All</div>
            <div className="artist-grid-show-all-count">12,500+ artists</div>

            {/* Decorative star */}
            <div className="artist-grid-show-all-star" aria-hidden="true">
              <Sparkles size={40} />
            </div>

            {/* Avatar bubbles */}
            <div className="artist-grid-show-all-avatars" aria-hidden="true">
              <img src="/artists/singer.png" alt="" className="artist-grid-show-all-avatar" />
              <img src="/artists/dj.png" alt="" className="artist-grid-show-all-avatar" />
              <img src="/artists/comedian.png" alt="" className="artist-grid-show-all-avatar" />
              <img src="/artists/anchor.png" alt="" className="artist-grid-show-all-avatar" />
            </div>
          </div>

          {rest.map((artist) => (
            <ArtistCard key={artist.artistId} artist={artist} />
          ))}
        </div>
      </div>
    </section>
  );
}
