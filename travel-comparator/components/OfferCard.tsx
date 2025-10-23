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

interface OfferCardProps {
  offer: Offer;
}

const OfferCard: React.FC<OfferCardProps> = ({ offer }) => {
  return (
    <div className="bg-white/95 backdrop-blur-sm p-4 sm:p-6 rounded-2xl shadow-xl border border-white/30 hover:shadow-2xl transition-all duration-300 hover:border-purple-300 hover:scale-105 group">
      <div className="flex flex-col h-full">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-md">
              🏢 {offer.agency}
            </span>
            {offer.duration_days && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                ⏱️ {offer.duration_days} days
              </span>
            )}
          </div>

          <h3 className="text-lg sm:text-xl font-bold mb-3 text-gray-800 line-clamp-2 leading-tight group-hover:text-purple-700 transition-colors">
            {offer.title}
          </h3>
        </div>

        <div className="flex items-center mb-4">
          <div className="bg-gradient-to-r from-green-400 to-emerald-500 p-2 rounded-lg mr-3 shadow-md">
            <span className="text-white text-lg">📍</span>
          </div>
          <span className="text-sm font-semibold text-gray-700 bg-green-50 px-3 py-1 rounded-full border border-green-200">
            {offer.destination}
          </span>
        </div>

        <div className="mb-4 p-3 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-600 font-medium uppercase tracking-wide">Price</div>
              <div className="text-2xl sm:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-600 to-emerald-600">
                €{offer.price_eur}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-600 font-medium">EUR</div>
              <div className="text-lg font-bold text-green-600">💰</div>
            </div>
          </div>
        </div>

        <div className="mb-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
          <div className="flex items-center mb-2">
            <span className="text-blue-600 mr-2">📅</span>
            <span className="text-sm font-semibold text-gray-700">Travel Dates</span>
          </div>
          <div className="text-sm text-gray-600">
            <div className="font-medium">{offer.dates_start || 'Not specified'}</div>
            <div className="text-gray-400">to</div>
            <div className="font-medium">{offer.dates_end || 'Not specified'}</div>
          </div>
        </div>

        <div className="mt-auto">
          <a
            href={offer.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center w-full bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white px-6 py-4 rounded-xl hover:from-purple-700 hover:via-pink-700 hover:to-red-700 transition-all shadow-lg font-bold text-sm sm:text-base transform hover:scale-105 group-hover:shadow-xl"
          >
            👀 View Full Details
            <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  );
};

export default OfferCard;