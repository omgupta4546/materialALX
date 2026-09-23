import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../App';

test('renders dashboard', () => {
  render(<App />);
  expect(screen.getByText(/National Material Hub/i)).toBeInTheDocument();
});
