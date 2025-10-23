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
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-2 border border-gray-300">{offer.agency}</td>
      <td className="px-4 py-2 border border-gray-300">{offer.title}</td>
      <td className="px-4 py-2 border border-gray-300">{offer.destination}</td>
      <td className="px-4 py-2 border border-gray-300">{offer.price_eur} EUR</td>
      <td className="px-4 py-2 border border-gray-300">{offer.dates_start} - {offer.dates_end}</td>
      <td className="px-4 py-2 border border-gray-300">
        <a href={offer.link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
          View
        </a>
      </td>
    </tr>
  );
};

export default OfferRow;