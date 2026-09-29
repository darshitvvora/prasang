import { useState } from 'react';
import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import CategoryPills from '../components/CategoryPills';
import ArtistGrid from '../components/ArtistGrid';
import Footer from '../components/Footer';
import QueryState from '../components/QueryState';
import { useSearchArtists } from '../api/queries';
import type { ArtistType } from '../types/artist';

export default function HomePage() {
  const [activeCategory, setActiveCategory] = useState<ArtistType | 'all'>('all');
  const artists = useSearchArtists({
    artistType: activeCategory === 'all' ? undefined : activeCategory,
    sort: 'relevance',
    size: 12,
  });

  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <CategoryPills activeCategory={activeCategory} onCategoryChange={setActiveCategory} />
        <QueryState query={artists}>
          {(data) => <ArtistGrid artists={data.items} total={activeCategory === 'all' ? data.total : undefined} />}
        </QueryState>
      </main>
      <Footer />
    </>
  );
}
