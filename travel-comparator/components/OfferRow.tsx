import React from 'react';

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

interface OfferRowProps {
  offer: Offer;
}

const OfferRow: React.FC<OfferRowProps> = ({ offer }) => {
  return (
    <tr className="hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 transition-all duration-200 border-b border-gray-100">
      <td className="px-4 sm:px-6 py-4 border-r border-gray-100">
        <div className="flex items-center">
          <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-lg mr-3 shadow-md">
            <span className="text-white text-sm">🏢</span>
          </div>
          <span className="font-bold text-purple-700 text-sm sm:text-base">{offer.agency}</span>
        </div>
      </td>

      <td className="px-4 sm:px-6 py-4 border-r border-gray-100">
        <div className="max-w-xs sm:max-w-sm lg:max-w-md">
          <div className="font-bold text-gray-800 text-sm sm:text-base line-clamp-2 mb-1 hover:text-purple-700 transition-colors">
            {offer.title}
          </div>
          {offer.duration_days && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              ⏱️ {offer.duration_days} days
            </span>
          )}
        </div>
      </td>

      <td className="px-4 sm:px-6 py-4 border-r border-gray-100">
        <div className="flex items-center">
          <div className="bg-gradient-to-r from-green-400 to-emerald-500 p-1.5 rounded-lg mr-2 shadow-sm">
            <span className="text-white text-xs">📍</span>
          </div>
          <span className="font-semibold text-green-700 text-sm sm:text-base bg-green-50 px-3 py-1 rounded-full border border-green-200">
            {offer.destination}
          </span>
        </div>
      </td>

      <td className="px-4 sm:px-6 py-4 border-r border-gray-100">
        <div className="bg-gradient-to-r from-yellow-400 to-orange-500 p-3 rounded-xl shadow-md">
          <div className="text-center">
            <div className="text-xs text-white font-bold uppercase tracking-wide">Price</div>
            <div className="text-lg sm:text-xl font-bold text-white">
              €{offer.price_eur}
            </div>
          </div>
        </div>
      </td>

      <td className="px-4 sm:px-6 py-4 border-r border-gray-100">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-3 rounded-xl border border-blue-200">
          <div className="text-xs sm:text-sm text-gray-600 mb-1 font-medium">📅 Travel Period</div>
          <div className="text-xs sm:text-sm text-gray-800 font-medium">
            {offer.dates_start || 'Not set'}
          </div>
          <div className="text-xs text-gray-400">to</div>
          <div className="text-xs sm:text-sm text-gray-800 font-medium">
            {offer.dates_end || 'Not set'}
          </div>
        </div>
      </td>

      <td className="px-4 sm:px-6 py-4">
        <a
          href={offer.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center px-4 py-3 bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white text-xs sm:text-sm font-bold rounded-xl hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all shadow-lg transform hover:scale-105"
        >
          👀 View Details
          <svg className="ml-2 w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </td>
    </tr>
  );
};

export default OfferRow;