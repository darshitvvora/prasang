import { useState, useMemo } from 'react';
import Navbar from '../components/Navbar';
import HeroSection from '../components/HeroSection';
import CategoryPills from '../components/CategoryPills';
import ArtistGrid from '../components/ArtistGrid';
import Footer from '../components/Footer';
import { mockArtists } from '../data/mockArtists';
import type { ArtistType } from '../types/artist';

export default function HomePage() {
  const [activeCategory, setActiveCategory] = useState<ArtistType | 'all'>('all');

  const filtered = useMemo(() => {
    if (activeCategory === 'all') return mockArtists;
    return mockArtists.filter((a) => a.artistType === activeCategory);
  }, [activeCategory]);

  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <CategoryPills activeCategory={activeCategory} onCategoryChange={setActiveCategory} />
        <ArtistGrid artists={filtered} />
      </main>
      <Footer />
    </>
  );
}
