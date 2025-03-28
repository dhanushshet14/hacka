/**
 * Date utility functions for formatting and manipulation
 */

/**
 * Format options for different date styles
 */
export const DATE_FORMATS = {
  short: { month: 'numeric', day: 'numeric', year: '2-digit' },
  medium: { month: 'short', day: 'numeric', year: 'numeric' },
  long: { month: 'long', day: 'numeric', year: 'numeric' },
  iso: { year: 'numeric', month: '2-digit', day: '2-digit' },
  time: { hour: '2-digit', minute: '2-digit' },
  timeWithSeconds: { hour: '2-digit', minute: '2-digit', second: '2-digit' },
  datetime: { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  },
  relative: {} // Special case handled separately
};

/**
 * Format a date according to the specified format
 * @param {Date|string|number} date - Date to format
 * @param {string|Object} format - Format name from DATE_FORMATS or Intl.DateTimeFormat options
 * @param {string} [locale] - Locale to use, defaults to browser locale
 * @returns {string} Formatted date
 */
export function formatDate(date, format = 'medium', locale = undefined) {
  if (!date) return '';
  
  try {
    // Convert to Date object if string or number
    const dateObj = typeof date === 'string' || typeof date === 'number'
      ? new Date(date)
      : date;
      
    // Check if valid date
    if (isNaN(dateObj.getTime())) {
      return '';
    }
    
    // Get format options
    const formatOptions = typeof format === 'string'
      ? (DATE_FORMATS[format] || DATE_FORMATS.medium)
      : format;
      
    // Special case for relative format
    if (format === 'relative') {
      return formatRelativeTime(dateObj);
    }
    
    // Use Intl.DateTimeFormat for localized formatting
    return new Intl.DateTimeFormat(locale, formatOptions).format(dateObj);
  } catch (error) {
    console.error('Error formatting date:', error);
    return '';
  }
}

/**
 * Format a date as a relative time (e.g. "2 hours ago")
 * @param {Date|string|number} date - Date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
  if (!date) return '';
  
  try {
    const dateObj = new Date(date);
    const now = new Date();
    const diffMs = now - dateObj;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    const diffMonth = Math.floor(diffDay / 30);
    const diffYear = Math.floor(diffDay / 365);
    
    // Future date
    if (diffMs < 0) {
      const absDiffSec = Math.abs(diffSec);
      const absDiffMin = Math.abs(diffMin);
      const absDiffHour = Math.abs(diffHour);
      const absDiffDay = Math.abs(diffDay);
      
      if (absDiffSec < 60) return 'in a few seconds';
      if (absDiffMin === 1) return 'in 1 minute';
      if (absDiffMin < 60) return `in ${absDiffMin} minutes`;
      if (absDiffHour === 1) return 'in 1 hour';
      if (absDiffHour < 24) return `in ${absDiffHour} hours`;
      if (absDiffDay === 1) return 'tomorrow';
      if (absDiffDay < 7) return `in ${absDiffDay} days`;
      
      // For distant future, use formatted date
      return formatDate(dateObj, 'medium');
    }
    
    // Past date
    if (diffSec < 10) return 'just now';
    if (diffSec < 60) return 'a few seconds ago';
    if (diffMin === 1) return '1 minute ago';
    if (diffMin < 60) return `${diffMin} minutes ago`;
    if (diffHour === 1) return '1 hour ago';
    if (diffHour < 24) return `${diffHour} hours ago`;
    if (diffDay === 1) return 'yesterday';
    if (diffDay < 7) return `${diffDay} days ago`;
    if (diffMonth === 1) return '1 month ago';
    if (diffMonth < 12) return `${diffMonth} months ago`;
    if (diffYear === 1) return '1 year ago';
    return `${diffYear} years ago`;
  } catch (error) {
    console.error('Error formatting relative time:', error);
    return '';
  }
}

/**
 * Get the start of a period (day, week, month, year)
 * @param {Date} [date] - Base date, defaults to now
 * @param {string} period - Period type: 'day', 'week', 'month', 'year'
 * @returns {Date} Start of the period
 */
export function startOf(date = new Date(), period = 'day') {
  const result = new Date(date);
  
  switch (period.toLowerCase()) {
    case 'day':
      result.setHours(0, 0, 0, 0);
      break;
    case 'week':
      const day = result.getDay(); // 0 = Sunday, 6 = Saturday
      result.setDate(result.getDate() - day); // Go to Sunday
      result.setHours(0, 0, 0, 0);
      break;
    case 'month':
      result.setDate(1);
      result.setHours(0, 0, 0, 0);
      break;
    case 'year':
      result.setMonth(0, 1);
      result.setHours(0, 0, 0, 0);
      break;
  }
  
  return result;
}

/**
 * Get the end of a period (day, week, month, year)
 * @param {Date} [date] - Base date, defaults to now
 * @param {string} period - Period type: 'day', 'week', 'month', 'year'
 * @returns {Date} End of the period
 */
export function endOf(date = new Date(), period = 'day') {
  const result = new Date(date);
  
  switch (period.toLowerCase()) {
    case 'day':
      result.setHours(23, 59, 59, 999);
      break;
    case 'week':
      const day = result.getDay();
      result.setDate(result.getDate() + (6 - day)); // Go to Saturday
      result.setHours(23, 59, 59, 999);
      break;
    case 'month':
      result.setMonth(result.getMonth() + 1, 0); // Last day of current month
      result.setHours(23, 59, 59, 999);
      break;
    case 'year':
      result.setFullYear(result.getFullYear() + 1, 0, 0); // First day of next year
      result.setTime(result.getTime() - 1); // Subtract 1ms to get last ms of current year
      break;
  }
  
  return result;
}

/**
 * Add time to a date
 * @param {Date} date - Base date
 * @param {number} amount - Amount to add
 * @param {string} unit - Unit: 'seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years'
 * @returns {Date} New date with added time
 */
export function addTime(date, amount, unit = 'days') {
  if (!date) return null;
  
  const result = new Date(date);
  
  switch (unit.toLowerCase()) {
    case 'seconds':
    case 'second':
      result.setSeconds(result.getSeconds() + amount);
      break;
    case 'minutes':
    case 'minute':
      result.setMinutes(result.getMinutes() + amount);
      break;
    case 'hours':
    case 'hour':
      result.setHours(result.getHours() + amount);
      break;
    case 'days':
    case 'day':
      result.setDate(result.getDate() + amount);
      break;
    case 'weeks':
    case 'week':
      result.setDate(result.getDate() + (amount * 7));
      break;
    case 'months':
    case 'month':
      result.setMonth(result.getMonth() + amount);
      break;
    case 'years':
    case 'year':
      result.setFullYear(result.getFullYear() + amount);
      break;
  }
  
  return result;
}

/**
 * Calculate the difference between two dates
 * @param {Date} date1 - First date
 * @param {Date} date2 - Second date
 * @param {string} unit - Unit for the result: 'seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'years'
 * @returns {number} Difference in the specified unit
 */
export function dateDiff(date1, date2, unit = 'days') {
  if (!date1 || !date2) return null;
  
  const d1 = new Date(date1);
  const d2 = new Date(date2);
  const diffMs = d2 - d1;
  
  switch (unit.toLowerCase()) {
    case 'seconds':
    case 'second':
      return Math.floor(diffMs / 1000);
    case 'minutes':
    case 'minute':
      return Math.floor(diffMs / 60000);
    case 'hours':
    case 'hour':
      return Math.floor(diffMs / 3600000);
    case 'days':
    case 'day':
      return Math.floor(diffMs / 86400000);
    case 'weeks':
    case 'week':
      return Math.floor(diffMs / (86400000 * 7));
    case 'months':
    case 'month': {
      const monthDiff = (d2.getFullYear() - d1.getFullYear()) * 12 + 
                         (d2.getMonth() - d1.getMonth());
      return monthDiff;
    }
    case 'years':
    case 'year':
      return d2.getFullYear() - d1.getFullYear();
    default:
      return diffMs;
  }
}

/**
 * Check if a date is between two other dates
 * @param {Date} date - Date to check
 * @param {Date} start - Start date
 * @param {Date} end - End date
 * @param {boolean} [inclusive=true] - Whether to include start and end dates
 * @returns {boolean} Whether the date is between start and end
 */
export function isBetween(date, start, end, inclusive = true) {
  if (!date || !start || !end) return false;
  
  const d = new Date(date).getTime();
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  
  return inclusive 
    ? d >= s && d <= e
    : d > s && d < e;
}

/**
 * Format a date range
 * @param {Date} startDate - Start date
 * @param {Date} endDate - End date
 * @param {string|Object} format - Format name or options
 * @param {string} [locale] - Locale to use
 * @returns {string} Formatted date range
 */
export function formatDateRange(startDate, endDate, format = 'medium', locale = undefined) {
  if (!startDate || !endDate) return '';
  
  const sameDay = startOf(startDate, 'day').getTime() === startOf(endDate, 'day').getTime();
  const sameMonth = 
    startDate.getMonth() === endDate.getMonth() && 
    startDate.getFullYear() === endDate.getFullYear();
  const sameYear = startDate.getFullYear() === endDate.getFullYear();
  
  // For same day, just show one date with time range
  if (sameDay) {
    const dateStr = formatDate(startDate, format === 'relative' ? 'medium' : format, locale);
    const startTime = formatDate(startDate, 'time', locale);
    const endTime = formatDate(endDate, 'time', locale);
    return `${dateStr}, ${startTime} - ${endTime}`;
  }
  
  // Special format for dates in same month
  if (sameMonth && format !== 'relative') {
    const monthYear = formatDate(startDate, { month: 'long', year: 'numeric' }, locale);
    const startDay = startDate.getDate();
    const endDay = endDate.getDate();
    return `${monthYear}, ${startDay}-${endDay}`;
  }
  
  // Special format for dates in same year
  if (sameYear && format !== 'relative') {
    const year = startDate.getFullYear();
    const startStr = formatDate(startDate, { month: 'short', day: 'numeric' }, locale);
    const endStr = formatDate(endDate, { month: 'short', day: 'numeric' }, locale);
    return `${startStr} - ${endStr}, ${year}`;
  }
  
  // Otherwise show full range
  const startStr = formatDate(startDate, format, locale);
  const endStr = formatDate(endDate, format, locale);
  return `${startStr} - ${endStr}`;
}

/**
 * Parse a date string in various formats
 * @param {string} dateStr - Date string to parse
 * @returns {Date|null} Parsed date or null if invalid
 */
export function parseDate(dateStr) {
  if (!dateStr) return null;
  
  // Try ISO format first
  const isoDate = new Date(dateStr);
  if (!isNaN(isoDate.getTime())) {
    return isoDate;
  }
  
  // Try MM/DD/YYYY format
  const parts = dateStr.split(/[\/\-\.]/);
  if (parts.length === 3) {
    // Assume MM/DD/YYYY
    const month = parseInt(parts[0], 10) - 1;
    const day = parseInt(parts[1], 10);
    const year = parseInt(parts[2], 10);
    
    // Add century if needed
    const fullYear = year < 100 ? (year < 50 ? 2000 + year : 1900 + year) : year;
    
    const date = new Date(fullYear, month, day);
    if (!isNaN(date.getTime())) {
      return date;
    }
    
    // Try DD/MM/YYYY
    const altDate = new Date(fullYear, day - 1, month + 1);
    if (!isNaN(altDate.getTime())) {
      return altDate;
    }
  }
  
  // Try natural language parsing as fallback
  try {
    const parsedDate = new Date(Date.parse(dateStr));
    if (!isNaN(parsedDate.getTime())) {
      return parsedDate;
    }
  } catch (e) {
    // Ignore parsing errors
  }
  
  return null;
}

/**
 * Format a duration in milliseconds to a human-readable string
 * @param {number} durationMs - Duration in milliseconds
 * @param {boolean} [verbose=false] - Whether to use verbose format
 * @returns {string} Formatted duration
 */
export function formatDuration(durationMs, verbose = false) {
  if (durationMs === undefined || durationMs === null) return '';
  
  const seconds = Math.floor((durationMs / 1000) % 60);
  const minutes = Math.floor((durationMs / (1000 * 60)) % 60);
  const hours = Math.floor((durationMs / (1000 * 60 * 60)) % 24);
  const days = Math.floor(durationMs / (1000 * 60 * 60 * 24));
  
  if (verbose) {
    const parts = [];
    
    if (days > 0) {
      parts.push(`${days} ${days === 1 ? 'day' : 'days'}`);
    }
    
    if (hours > 0) {
      parts.push(`${hours} ${hours === 1 ? 'hour' : 'hours'}`);
    }
    
    if (minutes > 0) {
      parts.push(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`);
    }
    
    if (seconds > 0 || parts.length === 0) {
      parts.push(`${seconds} ${seconds === 1 ? 'second' : 'seconds'}`);
    }
    
    return parts.join(', ');
  } else {
    // Short format (HH:MM:SS)
    const parts = [];
    
    if (days > 0) {
      parts.push(`${days}d`);
    }
    
    const hh = hours.toString().padStart(2, '0');
    const mm = minutes.toString().padStart(2, '0');
    const ss = seconds.toString().padStart(2, '0');
    
    if (days > 0 || hours > 0) {
      parts.push(`${hh}:${mm}:${ss}`);
    } else {
      parts.push(`${mm}:${ss}`);
    }
    
    return parts.join(' ');
  }
}

export default {
  formatDate,
  formatRelativeTime,
  startOf,
  endOf,
  addTime,
  dateDiff,
  isBetween,
  formatDateRange,
  parseDate,
  formatDuration,
  DATE_FORMATS
};