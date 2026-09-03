import React from 'react';
import { render, screen } from '@testing-library/react';
import { Navbar } from '../src/components/Navbar';
import { useAuth } from '../src/context/AuthContext';
import { usePathname } from 'next/navigation';

jest.mock('../src/context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
}));

describe('Navbar Role-Based Rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (usePathname as jest.Mock).mockReturnValue('/workflows');
  });

  it('does NOT render Dead Letters link for member role', () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { id: '1', email: 'member@example.com', role: 'member', is_active: true },
      isAuthenticated: true,
      logout: jest.fn(),
    });

    render(<Navbar />);

    expect(screen.getByText('Workflows')).toBeInTheDocument();
    expect(screen.getByText('Jobs')).toBeInTheDocument();
    expect(screen.queryByText('Dead Letters')).not.toBeInTheDocument();
  });

  it('renders Dead Letters link for admin role', () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { id: '2', email: 'admin@example.com', role: 'admin', is_active: true },
      isAuthenticated: true,
      logout: jest.fn(),
    });

    render(<Navbar />);

    expect(screen.getByText('Workflows')).toBeInTheDocument();
    expect(screen.getByText('Jobs')).toBeInTheDocument();
    expect(screen.getByText('Dead Letters')).toBeInTheDocument();
  });
});
