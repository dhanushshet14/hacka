/**
 * Utility functions for form validation
 */

/**
 * Validation error messages
 */
export const errorMessages = {
  required: 'This field is required',
  email: 'Please enter a valid email address',
  password: 'Password must be at least 8 characters with at least one letter and one number',
  passwordMatch: 'Passwords do not match',
  minLength: (min) => `Must be at least ${min} characters`,
  maxLength: (max) => `Must be no more than ${max} characters`,
  min: (min) => `Must be at least ${min}`,
  max: (max) => `Must be no more than ${max}`,
  pattern: 'Invalid format',
  url: 'Please enter a valid URL',
  numeric: 'Please enter a valid number',
  integer: 'Please enter a whole number',
  phoneNumber: 'Please enter a valid phone number',
  zipCode: 'Please enter a valid ZIP code',
};

/**
 * Validate a required field
 * @param {string} value - Field value to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const required = (value, message = errorMessages.required) => {
  if (value === undefined || value === null || value === '') {
    return message;
  }
  if (Array.isArray(value) && value.length === 0) {
    return message;
  }
  return null;
};

/**
 * Validate an email address
 * @param {string} value - Email to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const email = (value, message = errorMessages.email) => {
  if (!value) return null;
  
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(value) ? null : message;
};

/**
 * Validate a password
 * @param {string} value - Password to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const password = (value, message = errorMessages.password) => {
  if (!value) return null;
  
  // At least 8 characters, one letter and one number
  const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;
  return passwordRegex.test(value) ? null : message;
};

/**
 * Validate that passwords match
 * @param {string} value - Password confirmation value
 * @param {string} password - Original password value
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const passwordMatch = (value, password, message = errorMessages.passwordMatch) => {
  if (!value || !password) return null;
  return value === password ? null : message;
};

/**
 * Validate minimum length
 * @param {number} min - Minimum length
 * @param {string} [message] - Custom error message
 * @returns {function} Validator function
 */
export const minLength = (min, message) => (value) => {
  if (!value) return null;
  return String(value).length >= min ? null : (message || errorMessages.minLength(min));
};

/**
 * Validate maximum length
 * @param {number} max - Maximum length
 * @param {string} [message] - Custom error message
 * @returns {function} Validator function
 */
export const maxLength = (max, message) => (value) => {
  if (!value) return null;
  return String(value).length <= max ? null : (message || errorMessages.maxLength(max));
};

/**
 * Validate minimum value
 * @param {number} min - Minimum value
 * @param {string} [message] - Custom error message
 * @returns {function} Validator function
 */
export const min = (min, message) => (value) => {
  if (value === null || value === undefined || value === '') return null;
  return Number(value) >= min ? null : (message || errorMessages.min(min));
};

/**
 * Validate maximum value
 * @param {number} max - Maximum value
 * @param {string} [message] - Custom error message
 * @returns {function} Validator function
 */
export const max = (max, message) => (value) => {
  if (value === null || value === undefined || value === '') return null;
  return Number(value) <= max ? null : (message || errorMessages.max(max));
};

/**
 * Validate against a regex pattern
 * @param {RegExp} pattern - Regular expression to test
 * @param {string} [message] - Custom error message
 * @returns {function} Validator function
 */
export const pattern = (pattern, message = errorMessages.pattern) => (value) => {
  if (!value) return null;
  return pattern.test(value) ? null : message;
};

/**
 * Validate a URL
 * @param {string} value - URL to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const url = (value, message = errorMessages.url) => {
  if (!value) return null;
  
  try {
    new URL(value);
    return null;
  } catch (e) {
    return message;
  }
};

/**
 * Validate a numeric value
 * @param {string|number} value - Value to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const numeric = (value, message = errorMessages.numeric) => {
  if (value === null || value === undefined || value === '') return null;
  return !isNaN(Number(value)) ? null : message;
};

/**
 * Validate an integer value
 * @param {string|number} value - Value to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const integer = (value, message = errorMessages.integer) => {
  if (value === null || value === undefined || value === '') return null;
  return Number.isInteger(Number(value)) ? null : message;
};

/**
 * Validate a phone number
 * @param {string} value - Phone number to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const phoneNumber = (value, message = errorMessages.phoneNumber) => {
  if (!value) return null;
  
  // Basic international phone number validation
  const phoneRegex = /^\+?[0-9\s\-()]{8,20}$/;
  return phoneRegex.test(value) ? null : message;
};

/**
 * Validate a US ZIP code
 * @param {string} value - ZIP code to validate
 * @param {string} [message] - Custom error message
 * @returns {string|null} Error message or null if valid
 */
export const zipCode = (value, message = errorMessages.zipCode) => {
  if (!value) return null;
  
  // US ZIP code (5 digits or 5+4)
  const zipRegex = /^\d{5}(-\d{4})?$/;
  return zipRegex.test(value) ? null : message;
};

/**
 * Run multiple validators on a value
 * @param {any} value - Value to validate
 * @param {Array<function>} validators - Array of validator functions
 * @returns {string|null} First error message or null if all valid
 */
export const compose = (value, validators) => {
  for (const validator of validators) {
    const error = validator(value);
    if (error) {
      return error;
    }
  }
  return null;
};

/**
 * Validate an entire form
 * @param {object} values - Form values
 * @param {object} validationSchema - Validation schema
 * @returns {object} Object with validation errors
 */
export const validateForm = (values, validationSchema) => {
  const errors = {};
  
  for (const key in validationSchema) {
    if (Object.prototype.hasOwnProperty.call(validationSchema, key)) {
      const value = values[key];
      const validator = validationSchema[key];
      
      if (typeof validator === 'function') {
        const error = validator(value, values);
        if (error) {
          errors[key] = error;
        }
      } else if (Array.isArray(validator)) {
        const error = compose(value, validator.map(v => 
          typeof v === 'function' ? v : v.validator
        ));
        if (error) {
          errors[key] = error;
        }
      }
    }
  }
  
  return errors;
};

export default {
  required,
  email,
  password,
  passwordMatch,
  minLength,
  maxLength,
  min,
  max,
  pattern,
  url,
  numeric,
  integer,
  phoneNumber,
  zipCode,
  compose,
  validateForm,
  errorMessages,
}; 