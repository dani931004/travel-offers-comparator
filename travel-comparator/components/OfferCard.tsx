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
    <div className="bg-white/95 backdrop-blur-sm p-4 sm:p-6 rounded-2xl shadow-xl border border-white/30 hover:shadow-2xl transition-all duration-300 hover:border-primary-teal hover:scale-105 group">
      <div className="flex flex-col h-full">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-primary-teal text-white shadow-md">
              {offer.agency === 'Aratur' ? '🦜' : '🏢'} {offer.agency}
            </span>
            {offer.duration_days && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-teal/10 text-primary-teal">
                ⏱️ {offer.duration_days} days
              </span>
            )}
          </div>

          <h3 
            className="text-lg sm:text-xl font-bold mb-3 text-gray-800 leading-tight group-hover:text-primary-teal transition-colors"
          >
            {offer.title}
          </h3>
        </div>

        <div className="flex items-center mb-4">
          <div className="bg-primary-teal p-2 rounded-lg mr-3 shadow-md">
            <span className="text-white text-lg">📍</span>
          </div>
          <span className="text-sm font-semibold text-primary-teal bg-primary-teal/10 px-3 py-1 rounded-full border border-primary-teal/30">
            {offer.destination}
          </span>
        </div>

        <div className="mb-4 p-3 bg-primary-teal/5 rounded-xl border border-primary-teal/20">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-600 font-medium uppercase tracking-wide">Price</div>
              <div className="text-2xl sm:text-3xl font-bold text-primary-teal">
                €{offer.price_eur}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-600 font-medium">EUR</div>
              <div className="text-lg font-bold text-primary-teal">💰</div>
            </div>
          </div>
        </div>

        <div className="mb-4 p-3 bg-white rounded-xl border border-gray-200">
          <div className="flex items-center mb-2">
            <span className="text-trust-navy mr-2">📅</span>
            <span className="text-sm font-semibold text-gray-700">Travel Dates</span>
            {offer.duration_days && (
              <span className="ml-auto inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-trust-navy/10 text-trust-navy">
                ⏱️ {offer.duration_days} days
              </span>
            )}
          </div>
          <div className="text-sm text-gray-600">
            <div className="font-medium">
              {offer.dates_start ? new Date(offer.dates_start).toLocaleDateString('en-GB') : 'Not specified'}
            </div>
            <div className="text-gray-400">to</div>
            <div className="font-medium">
              {offer.dates_end ? new Date(offer.dates_end).toLocaleDateString('en-GB') : 'Not specified'}
            </div>
          </div>
        </div>

        <div className="mt-auto">
          <a
            href={offer.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center w-full bg-accent-coral text-white px-6 py-4 rounded-xl hover:bg-accent-coral/90 transition-all shadow-lg font-bold text-sm sm:text-base transform hover:scale-105 group-hover:shadow-xl"
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