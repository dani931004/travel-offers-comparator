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
    <tr className="hover:bg-blue-50 transition-colors">
      <td className="px-3 sm:px-4 py-3 border border-gray-200 text-sm sm:text-base">
        <span className="font-medium text-blue-700">{offer.agency}</span>
      </td>
      <td className="px-3 sm:px-4 py-3 border border-gray-200">
        <div className="max-w-xs sm:max-w-sm lg:max-w-md">
          <div className="font-semibold text-gray-800 text-sm sm:text-base line-clamp-2">{offer.title}</div>
        </div>
      </td>
      <td className="px-3 sm:px-4 py-3 border border-gray-200 text-sm sm:text-base">
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          📍 {offer.destination}
        </span>
      </td>
      <td className="px-3 sm:px-4 py-3 border border-gray-200">
        <span className="font-bold text-green-600 text-sm sm:text-base">€{offer.price_eur}</span>
      </td>
      <td className="px-3 sm:px-4 py-3 border border-gray-200 text-xs sm:text-sm text-gray-600">
        <div className="flex flex-col">
          <span>{offer.dates_start || 'N/A'}</span>
          <span className="text-gray-400">to</span>
          <span>{offer.dates_end || 'N/A'}</span>
        </div>
      </td>
      <td className="px-3 sm:px-4 py-3 border border-gray-200">
        <a 
          href={offer.link} 
          target="_blank" 
          rel="noopener noreferrer"
          className="inline-flex items-center px-3 py-2 bg-blue-600 text-white text-xs sm:text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          👀 View
        </a>
      </td>
    </tr>
  );
};

export default OfferRow;