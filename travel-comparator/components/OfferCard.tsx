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
    <div className="bg-white p-4 sm:p-6 rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300 hover:border-blue-200">
      <div className="flex flex-col h-full">
        <h3 className="text-lg sm:text-xl font-bold mb-3 text-gray-800 line-clamp-2 leading-tight">{offer.title}</h3>
        
        <div className="flex items-center mb-2">
          <span className="text-sm font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
            🏢 {offer.agency}
          </span>
        </div>
        
        <div className="flex items-center mb-3">
          <span className="text-sm font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
            📍 {offer.destination}
          </span>
        </div>
        
        <div className="mb-3">
          <span className="text-2xl sm:text-3xl font-bold text-green-600">
            €{offer.price_eur}
          </span>
          <span className="text-sm text-gray-500 ml-1">EUR</span>
        </div>
        
        <div className="mb-4">
          <div className="flex items-center text-sm text-gray-600 mb-1">
            <span className="mr-2">📅</span>
            <span>{offer.dates_start || 'N/A'} - {offer.dates_end || 'N/A'}</span>
          </div>
          {offer.duration_days && (
            <div className="flex items-center text-sm text-gray-600">
              <span className="mr-2">⏱️</span>
              <span>{offer.duration_days} days</span>
            </div>
          )}
        </div>
        
        <div className="mt-auto">
          <a 
            href={offer.link} 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-3 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md font-medium text-sm sm:text-base"
          >
            👀 View Details
          </a>
        </div>
      </div>
    </div>
  );
};

export default OfferCard;