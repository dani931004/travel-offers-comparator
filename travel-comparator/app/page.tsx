'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useDebounce } from '../hooks/useDebounce';

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
  const [searchTermInput, setSearchTermInput] = useState('');
  const debouncedSearchTerm = useDebounce(searchTermInput, 300);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table');

  // Utility function to calculate duration from dates
  const calculateDuration = (startDate: string, endDate: string): number | null => {
    if (!startDate || !endDate) return null;
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return null;
    
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays;
  };

  // Load data on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await fetch('/travel-offers-comparator/data.json');
        const data = await response.json();
        // Calculate duration for offers that don't have it
        const processedData = data.map((offer: Offer) => ({
          ...offer,
          duration_days: offer.duration_days || calculateDuration(offer.dates_start, offer.dates_end)
        }));
        setAllOffers(processedData);
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Sync debounced search term to the main filters state
  useEffect(() => {
    if (filters.search !== debouncedSearchTerm) {
      setFilters(prevFilters => ({
        ...prevFilters,
        search: debouncedSearchTerm,
      }));
    }
  }, [debouncedSearchTerm, filters.search]);

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (name === 'search') {
      setSearchTermInput(value);
    } else {
      setFilters({ ...filters, [name]: value });
    }
  };

  // Filter offers client-side
  const offers = useMemo(() => {
    // Only show offers if at least one filter is active
    const hasActiveFilters = filters.search.trim() !== '' || 
                           filters.min_price !== '' || 
                           filters.max_price !== '' || 
                           filters.start_date !== '' || 
                           filters.end_date !== '';

    if (!hasActiveFilters) {
      return [];
    }

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
    }).sort((a, b) => a.price_eur - b.price_eur);
  }, [allOffers, filters]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-400 via-pink-500 to-red-500 p-2 sm:p-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-2 drop-shadow-lg">
            🌟 Travel Offers Comparator
          </h1>
          <p className="text-white/90 text-sm sm:text-base font-medium">
            Discover amazing deals from top Bulgarian travel agencies
          </p>
        </div>

        <div className="bg-white/95 backdrop-blur-sm p-4 sm:p-6 rounded-2xl shadow-2xl mb-6 sm:mb-8 border border-white/20">
          <div className="flex items-center mb-6">
            <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-lg mr-3">
              <span className="text-white text-xl">🔍</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-gray-800">Search & Filter Offers</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 sm:gap-4 mb-6">
            <div className="col-span-1 sm:col-span-2 lg:col-span-3 xl:col-span-2 relative">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Search Destinations & Titles</label>
              <div className="relative">
                <input
                  type="text"
                  name="search"
                  placeholder="Try 'Albania', 'New Year', 'Christmas'..."
                  value={searchTermInput}
                  onChange={handleFilterChange}
                  className="w-full pl-12 pr-4 py-3 border-2 border-purple-200 rounded-xl focus:ring-4 focus:ring-purple-300 focus:border-purple-500 transition-all bg-white/80 backdrop-blur-sm text-gray-800 placeholder-gray-500"
                />
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-purple-500">
                  🔍
                </div>
              </div>
            </div>

            <div className="relative">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Min Price (€)</label>
              <div className="relative">
                <input
                  type="number"
                  name="min_price"
                  placeholder="0"
                  value={filters.min_price}
                  onChange={handleFilterChange}
                  className="w-full pl-8 pr-4 py-3 border-2 border-green-200 rounded-xl focus:ring-4 focus:ring-green-300 focus:border-green-500 transition-all bg-white/80 backdrop-blur-sm text-gray-800 placeholder-gray-500"
                />
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-green-500 font-bold">
                  €
                </div>
              </div>
            </div>

            <div className="relative">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Max Price (€)</label>
              <div className="relative">
                <input
                  type="number"
                  name="max_price"
                  placeholder="5000"
                  value={filters.max_price}
                  onChange={handleFilterChange}
                  className="w-full pl-8 pr-4 py-3 border-2 border-green-200 rounded-xl focus:ring-4 focus:ring-green-300 focus:border-green-500 transition-all bg-white/80 backdrop-blur-sm text-gray-800 placeholder-gray-500"
                />
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-green-500 font-bold">
                  €
                </div>
              </div>
            </div>

            <div className="relative">
              <label className="block text-sm font-semibold text-gray-700 mb-2">Start Date</label>
              <input
                type="date"
                name="start_date"
                value={filters.start_date}
                onChange={handleFilterChange}
                className="w-full px-4 py-3 border-2 border-blue-200 rounded-xl focus:ring-4 focus:ring-blue-300 focus:border-blue-500 transition-all bg-white/80 backdrop-blur-sm text-gray-800"
              />
            </div>

            <div className="relative">
              <label className="block text-sm font-semibold text-gray-700 mb-2">End Date</label>
              <input
                type="date"
                name="end_date"
                value={filters.end_date}
                onChange={handleFilterChange}
                className="w-full px-4 py-3 border-2 border-blue-200 rounded-xl focus:ring-4 focus:ring-blue-300 focus:border-blue-500 transition-all bg-white/80 backdrop-blur-sm text-gray-800"
              />
            </div>
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border border-purple-100">
            <div className="flex items-center">
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-lg mr-3">
                <span className="text-white">📊</span>
              </div>
              <div>
                <div className="text-lg font-bold text-gray-800">
                  {offers.length > 0 ? (
                    <>
                      <span className="text-purple-600">{offers.length}</span> Amazing Offers Found
                    </>
                  ) : (
                    <>
                      <span className="text-purple-600">{allOffers.length}</span> Offers Available
                    </>
                  )}
                </div>
                <div className="text-sm text-gray-600">
                  {offers.length > 0 ? 'From 3 top Bulgarian agencies' : 'Apply filters to see results'}
                </div>
              </div>
            </div>

            <button
              onClick={() => setViewMode(viewMode === 'grid' ? 'table' : 'grid')}
              className="bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white px-6 py-3 rounded-xl hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all shadow-lg font-bold transform hover:scale-105"
            >
              🔄 {viewMode === 'grid' ? '📋 Table View' : '🎴 Grid View'}
            </button>
          </div>
        </div>

      <div className="max-w-6xl mx-auto">
        {offers.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-bold text-gray-700 mb-2">Start Your Search</h3>
            <p className="text-gray-500">Use the filters above to find amazing travel offers from top Bulgarian agencies</p>
          </div>
        )}
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {offers.map((offer, index) => (
              <OfferCard key={`${offer.id}-${index}`} offer={offer} />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl border border-white/30">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white">
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base border-r border-white/20">🏢 Agency</th>
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base border-r border-white/20">📝 Offer Details</th>
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base border-r border-white/20">📍 Destination</th>
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base border-r border-white/20">💰 Price</th>
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base border-r border-white/20">📅 Travel Dates</th>
                  <th className="px-4 sm:px-6 py-4 text-left font-bold text-sm sm:text-base">🔗 Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {offers.map((offer, index) => (
                  <OfferRow key={`${offer.id}-${index}`} offer={offer} />
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