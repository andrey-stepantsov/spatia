import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import ContentModal from './ContentModal';

// Mock clipboard
Object.assign(navigator, {
    clipboard: {
        writeText: vi.fn(),
    },
});

describe('ContentModal', () => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
        content: 'def hello():\n    print("world")',
        language: 'python',
        title: 'test.py'
    };

    it('renders nothing when not open', () => {
        const { container } = render(<ContentModal {...defaultProps} isOpen={false} />);
        expect(container).toBeEmptyDOMElement();
    });

    it('renders content when open', () => {
        render(<ContentModal {...defaultProps} />);
        expect(screen.getByText('test.py')).toBeInTheDocument();
        expect(screen.getByText('python')).toBeInTheDocument();

        // SyntaxHighlighter renders content in spans, but text should be present
        expect(screen.getByText(/def hello/)).toBeInTheDocument();
        expect(screen.getByText(/print/)).toBeInTheDocument();
    });

    it('calls onClose when close button is clicked', () => {
        render(<ContentModal {...defaultProps} />);
        const closeBtn = screen.getByText('✕');
        fireEvent.click(closeBtn);
        expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it('copies content to clipboard', async () => {
        render(<ContentModal {...defaultProps} />);
        const copyBtn = screen.getByText('Copy');
        fireEvent.click(copyBtn);
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(defaultProps.content);
    });
});
