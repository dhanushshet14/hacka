import { useState, useCallback } from 'react';

/**
 * Custom hook for managing form state and validation
 * 
 * @param {Object} initialValues - Initial form values
 * @param {Function} onSubmit - Submit handler function
 * @param {Function} validate - Optional validation function
 * @returns {Object} Form state and handlers
 */
export const useForm = ({
  initialValues,
  validate,
  onSubmit
}) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState({});

  // Handle input changes
  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    
    setValues((prev) => ({
      ...prev,
      [name]: value,
    }));
  }, []);

  // Handle blur events for field-level validation
  const handleBlur = useCallback((e) => {
    const { name } = e.target;
    
    setTouched((prev) => ({
      ...prev,
      [name]: true,
    }));
    
    // If validate function is provided, validate on blur
    if (validate) {
      const validationErrors = validate(values);
      setErrors(validationErrors);
    }
  }, [validate, values]);

  // Reset the form to initial values
  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  // Set a specific field value
  const setFieldValue = useCallback((name, value) => {
    setValues((prev) => ({
      ...prev,
      [name]: value,
    }));
  }, []);

  // Handle form submission
  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    
    // Validate if validation function is provided
    if (validate) {
      const validationErrors = validate(values);
      setErrors(validationErrors);
      
      // Mark all fields as touched on submit
      const touchedFields = {};
      Object.keys(values).forEach((key) => {
        touchedFields[key] = true;
      });
      setTouched(touchedFields);
      
      // If there are errors, don't submit
      if (Object.keys(validationErrors).length > 0) {
        return;
      }
    }
    
    setIsSubmitting(true);
    
    try {
      await onSubmit(values);
    } catch (error) {
      console.error('Form submission error:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [validate, values, onSubmit]);

  return {
    values,
    errors,
    touched,
    loading: isSubmitting,
    isSubmitting,
    handleChange,
    handleBlur,
    handleSubmit,
    resetForm,
    setFieldValue,
  };
}; 