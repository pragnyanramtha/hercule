import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Settings, { useUserSettings } from '../../popup/components/Settings';
import { renderHook } from '@testing-library/react';

// ============== Settings Component Tests ==============

describe('Settings Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Mock storage.local.get to return empty settings
        (chrome.storage.local.get as ReturnType<typeof vi.fn>).mockImplementation(
            (_keys: string[], callback: (result: Record<string, unknown>) => void) => {
                callback({});
            }
        );
        // Mock storage.local.set to call callback
        (chrome.storage.local.set as ReturnType<typeof vi.fn>).mockImplementation(
            (_data: Record<string, unknown>, callback?: () => void) => {
                if (callback) callback();
            }
        );
    });

    describe('Rendering', () => {
        it('should not render when isOpen is false', () => {
            const { container } = render(<Settings isOpen={false} onClose={() => { }} />);
            expect(container.firstChild).toBeNull();
        });

        it('should render when isOpen is true', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            expect(screen.getByText('Settings')).toBeInTheDocument();
        });

        it('should render name input field', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument();
        });

        it('should render API key input field', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            expect(screen.getByPlaceholderText('gsk_...')).toBeInTheDocument();
        });

        it('should render Save and Clear buttons', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            expect(screen.getByText('Save Settings')).toBeInTheDocument();
            expect(screen.getByText('Clear')).toBeInTheDocument();
        });
    });

    describe('User Interactions', () => {
        it('should call onClose when close button is clicked', () => {
            const onClose = vi.fn();
            render(<Settings isOpen={true} onClose={onClose} />);

            // Find the close button (X icon)
            const closeButtons = screen.getAllByRole('button');
            const closeButton = closeButtons.find(btn => btn.getAttribute('title') !== 'Settings');
            if (closeButton) fireEvent.click(closeButton);

            expect(onClose).toHaveBeenCalled();
        });

        it('should allow typing in name field', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            const nameInput = screen.getByPlaceholderText('John Doe') as HTMLInputElement;

            fireEvent.change(nameInput, { target: { value: 'Test User' } });
            expect(nameInput.value).toBe('Test User');
        });

        it('should allow typing in API key field', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            const apiKeyInput = screen.getByPlaceholderText('gsk_...') as HTMLInputElement;

            fireEvent.change(apiKeyInput, { target: { value: 'gsk_test123' } });
            expect(apiKeyInput.value).toBe('gsk_test123');
        });

        it('should save settings when Save button is clicked', async () => {
            render(<Settings isOpen={true} onClose={() => { }} />);

            // Fill in the form
            const nameInput = screen.getByPlaceholderText('John Doe');
            const apiKeyInput = screen.getByPlaceholderText('gsk_...');

            fireEvent.change(nameInput, { target: { value: 'Test User' } });
            fireEvent.change(apiKeyInput, { target: { value: 'gsk_test_key' } });

            // Click save
            fireEvent.click(screen.getByText('Save Settings'));

            // Verify storage.local.set was called
            await waitFor(() => {
                expect(chrome.storage.local.set).toHaveBeenCalledWith(
                    expect.objectContaining({
                        hercule_user_settings: {
                            userName: 'Test User',
                            groqApiKey: 'gsk_test_key',
                        }
                    }),
                    expect.any(Function)
                );
            });
        });

        it('should clear fields when Clear button is clicked', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);

            // Fill in the form
            const nameInput = screen.getByPlaceholderText('John Doe') as HTMLInputElement;
            const apiKeyInput = screen.getByPlaceholderText('gsk_...') as HTMLInputElement;

            fireEvent.change(nameInput, { target: { value: 'Test User' } });
            fireEvent.change(apiKeyInput, { target: { value: 'gsk_test_key' } });

            // Click clear
            fireEvent.click(screen.getByText('Clear'));

            expect(nameInput.value).toBe('');
            expect(apiKeyInput.value).toBe('');
        });

        it('should show "Saved!" after successful save', async () => {
            render(<Settings isOpen={true} onClose={() => { }} />);

            fireEvent.click(screen.getByText('Save Settings'));

            await waitFor(() => {
                expect(screen.getByText('Saved!')).toBeInTheDocument();
            });
        });
    });

    describe('Loading Settings', () => {
        it('should load existing settings on mount', async () => {
            // Mock storage to return existing settings
            (chrome.storage.local.get as ReturnType<typeof vi.fn>).mockImplementation(
                (_keys: string[], callback: (result: Record<string, unknown>) => void) => {
                    callback({
                        hercule_user_settings: {
                            userName: 'Existing User',
                            groqApiKey: 'gsk_existing_key',
                        }
                    });
                }
            );

            render(<Settings isOpen={true} onClose={() => { }} />);

            await waitFor(() => {
                const nameInput = screen.getByPlaceholderText('John Doe') as HTMLInputElement;
                const apiKeyInput = screen.getByPlaceholderText('gsk_...') as HTMLInputElement;

                expect(nameInput.value).toBe('Existing User');
                expect(apiKeyInput.value).toBe('gsk_existing_key');
            });
        });
    });

    describe('API Key Visibility', () => {
        it('should hide API key by default', () => {
            render(<Settings isOpen={true} onClose={() => { }} />);
            const apiKeyInput = screen.getByPlaceholderText('gsk_...');
            expect(apiKeyInput).toHaveAttribute('type', 'password');
        });
    });
});


// ============== useUserSettings Hook Tests ==============

describe('useUserSettings Hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default mock: return empty settings
        (chrome.storage.local.get as ReturnType<typeof vi.fn>).mockImplementation(
            (_keys: string[], callback: (result: Record<string, unknown>) => void) => {
                callback({});
            }
        );
    });

    it('should return empty settings by default', () => {
        const { result } = renderHook(() => useUserSettings());

        expect(result.current.userName).toBe('');
        expect(result.current.groqApiKey).toBe('');
    });

    it('should load settings from storage', async () => {
        (chrome.storage.local.get as ReturnType<typeof vi.fn>).mockImplementation(
            (_keys: string[], callback: (result: Record<string, unknown>) => void) => {
                callback({
                    hercule_user_settings: {
                        userName: 'Hook User',
                        groqApiKey: 'gsk_hook_key',
                    }
                });
            }
        );

        const { result } = renderHook(() => useUserSettings());

        await waitFor(() => {
            expect(result.current.userName).toBe('Hook User');
            expect(result.current.groqApiKey).toBe('gsk_hook_key');
        });
    });

    it('should register storage change listener', () => {
        renderHook(() => useUserSettings());

        expect(chrome.storage.onChanged.addListener).toHaveBeenCalled();
    });

    it('should cleanup listener on unmount', () => {
        const { unmount } = renderHook(() => useUserSettings());

        unmount();

        expect(chrome.storage.onChanged.removeListener).toHaveBeenCalled();
    });
});
