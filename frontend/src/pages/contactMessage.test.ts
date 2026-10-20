import { describe, expect, it } from 'vitest';
import { buildContactRequest, emptyContact, validateContact } from './contactMessage';

const valid = { ...emptyContact, name: 'Riya Shah', contact: 'riya@example.com', message: 'I paid but my plan shows Free.' };

describe('validateContact', () => {
  it('accepts a complete message', () => {
    expect(validateContact(valid)).toEqual({});
  });
  it('asks for at least 10 characters of message', () => {
    expect(validateContact({ ...valid, message: 'short' })).toEqual({ message: 'Please write at least 10 characters' });
  });
  it('needs a name', () => {
    expect(validateContact({ ...valid, name: '  ' }).name).toBe('Please enter your name');
  });
  it('needs a valid phone or email', () => {
    expect(validateContact({ ...valid, contact: 'abc' }).contact).toBe('Enter a 10-digit mobile number or an email address');
    expect(validateContact({ ...valid, contact: '9820012345' })).toEqual({});
  });
});

describe('buildContactRequest', () => {
  it('trims fields', () => {
    expect(buildContactRequest({ ...valid, name: ' Riya ', message: '  I paid but my plan shows Free. ' })).toEqual({
      name: 'Riya', contact: 'riya@example.com', topic: 'general', message: 'I paid but my plan shows Free.',
    });
  });
});
