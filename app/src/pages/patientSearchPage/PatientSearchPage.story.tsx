import type { Meta, StoryObj } from '@storybook/react';
import Component from './PatientSearchPage';
import { USER_ROLE } from '../../types/generic/roles';
import { AUTH_ROLE } from '../../types/generic/authRole';

const meta = {
    title: 'Pages/PatientSearchPage',
    component: Component,
    tags: ['autodocs'],
    parameters: {
        layout: 'fullscreen',
    },
} satisfies Meta<typeof Component>;

type Story = StoryObj<typeof meta>;

export const PatientSearchPage: Story = {
    args: {
        role: AUTH_ROLE.PCSE,
    },
};
export default meta;
