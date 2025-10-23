'use client';

import React, { useState, useEffect, useMemo } from 'react';

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
  const [allOffers, setAllOffers] = useState<Offer[]>([]);
  const [filters, setFilters] = useState({
    search: '',
    min_price: '',
    max_price: '',
    start_date: '',
    end_date: '',
  });
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await fetch('/travel-offers-comparator/data.json');
        const data = await response.json();
        setAllOffers(data);
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  // Filter offers client-side
  const offers = useMemo(() => {
    return allOffers.filter((offer) => {
      // Search filter (searches in both destination and title, case-insensitive)
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase();
        const destinationMatch = offer.destination.toLowerCase().includes(searchTerm);
        const titleMatch = offer.title.toLowerCase().includes(searchTerm);
        if (!destinationMatch && !titleMatch) {
          return false;
        }
      }

      // Price filters
      if (filters.min_price && offer.price_eur < parseFloat(filters.min_price)) {
        return false;
      }
      if (filters.max_price && offer.price_eur > parseFloat(filters.max_price)) {
        return false;
      }

      // Date filters
      if (filters.start_date && offer.dates_start && offer.dates_start < filters.start_date) {
        return false;
      }
      if (filters.end_date && offer.dates_end && offer.dates_end > filters.end_date) {
        return false;
      }

      return true;
    });
  }, [allOffers, filters]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-2 sm:p-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-center mb-6 sm:mb-8 text-blue-900">✈️ Travel Offers Comparator</h1>

        <div className="bg-white p-4 sm:p-6 rounded-xl shadow-lg mb-6 sm:mb-8 border border-blue-100">
          <h2 className="text-lg sm:text-xl font-semibold mb-4 text-gray-800">🔍 Search & Filter Offers</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 sm:gap-4 mb-4">
            <div className="col-span-1 sm:col-span-2 lg:col-span-3 xl:col-span-2">
              <input
                type="text"
                name="search"
                placeholder="Search destinations or titles..."
                value={filters.search}
                onChange={handleFilterChange}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
            </div>
            <input
              type="number"
              name="min_price"
              placeholder="Min Price (EUR)"
              value={filters.min_price}
              onChange={handleFilterChange}
              className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <input
              type="number"
              name="max_price"
              placeholder="Max Price (EUR)"
              value={filters.max_price}
              onChange={handleFilterChange}
              className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <input
              type="date"
              name="start_date"
              value={filters.start_date}
              onChange={handleFilterChange}
              className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <input
              type="date"
              name="end_date"
              value={filters.end_date}
              onChange={handleFilterChange}
              className="p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div className="text-sm sm:text-base text-gray-600 font-medium">
              📊 Found <span className="text-blue-600 font-bold">{offers.length}</span> offers matching your criteria
            </div>
            <button
              onClick={() => setViewMode(viewMode === 'grid' ? 'table' : 'grid')}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md font-medium"
            >
              🔄 Switch to {viewMode === 'grid' ? 'Table' : 'Grid'} View
            </button>
          </div>
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
    </div>
  );
}