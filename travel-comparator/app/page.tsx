'use client';

import React, { useState, useEffect } from 'react';

import OfferCard from '../components/OfferCard';
import OfferRow from '../components/OfferRow';

interface Offer {
  id: string;
  agency: string;
  title: string;
  destination: string;
  price_eur: number;
  dates_start: string;
  dates_end: string;
  duration_days: number;
  program_info: string;
  price_includes: string[];
  price_excludes: string[];
  hotel_titles: string[];
  booking_conditions: string;
  link: string;
  scraped_at: string;
}

export default function Home() {
  const [offers, setOffers] = useState<Offer[]>([]);
  const [filters, setFilters] = useState({
    destination: '',
    min_price: '',
    max_price: '',
    start_date: '',
    end_date: '',
  });
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');

  useEffect(() => {
    searchOffers();
  }, [filters]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const searchOffers = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    try {
      const res = await fetch(`/api/offers?${params}`);
      if (!res.ok) {
        throw new Error('Failed to fetch offers');
      }
      const data = await res.json();
      setOffers(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching offers:', error);
      setOffers([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-blue-50 p-4">
      <h1 className="text-3xl font-bold text-center mb-8 text-blue-800">Travel Offers Comparator</h1>

      <div className="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow-md mb-8">
        <h2 className="text-xl font-semibold mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <input
            type="text"
            name="destination"
            placeholder="Destination (e.g., Albania)"
            value={filters.destination}
            onChange={handleFilterChange}
            className="p-2 border rounded"
          />
          <input
            type="number"
            name="min_price"
            placeholder="Min Price (EUR)"
            value={filters.min_price}
            onChange={handleFilterChange}
            className="p-2 border rounded"
          />
          <input
            type="number"
            name="max_price"
            placeholder="Max Price (EUR)"
            value={filters.max_price}
            onChange={handleFilterChange}
            className="p-2 border rounded"
          />
          <input
            type="date"
            name="start_date"
            value={filters.start_date}
            onChange={handleFilterChange}
            className="p-2 border rounded"
          />
          <input
            type="date"
            name="end_date"
            value={filters.end_date}
            onChange={handleFilterChange}
            className="p-2 border rounded"
          />
        </div>
        <button
          onClick={searchOffers}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          disabled={loading}
        >
          {loading ? 'Searching...' : 'Search Offers'}
        </button>
      </div>

      <div className="max-w-6xl mx-auto mb-4">
        <button
          onClick={() => setViewMode(viewMode === 'grid' ? 'table' : 'grid')}
          className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
        >
          Switch to {viewMode === 'grid' ? 'Table' : 'Grid'} View
        </button>
      </div>

      <div className="max-w-6xl mx-auto">
        {offers.length === 0 && !loading && <p className="text-center">No offers found. Try adjusting filters.</p>}
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {offers.map((offer) => (
              <OfferCard key={offer.id} offer={offer} />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Agency</th>
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Title</th>
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Destination</th>
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Price</th>
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Dates</th>
                  <th className="px-4 py-3 border border-gray-300 text-left font-semibold text-gray-800">Link</th>
                </tr>
              </thead>
              <tbody>
                {offers.map((offer) => (
                  <OfferRow key={offer.id} offer={offer} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}