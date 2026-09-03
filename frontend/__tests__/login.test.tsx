import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '../src/app/login/page';
import { useAuth } from '../src/context/AuthContext';
import { useRouter } from 'next/navigation';

jest.mock('../src/context/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

describe('LoginPage Form Component', () => {
  const mockPush = jest.fn();
  const mockLogin = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
    (useAuth as jest.Mock).mockReturnValue({ login: mockLogin });
  });

  it('renders login form inputs and sign in button', () => {
    render(<LoginPage />);

    expect(screen.getByPlaceholderText('user@example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('displays error message banner when login fails on bad credentials', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Incorrect email or password'));

    render(<LoginPage />);

    fireEvent.change(screen.getByPlaceholderText('user@example.com'), {
      target: { value: 'baduser@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'wrongpassword' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Incorrect email or password')).toBeInTheDocument();
    });

    expect(mockPush).not.toHaveBeenCalled();
  });
});
