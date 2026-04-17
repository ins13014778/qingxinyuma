import 'zone.js/testing';
import { getTestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

type WebpackContext = {
  keys(): string[];
  <T>(id: string): T;
};

declare global {
  interface ImportMeta {
    webpackContext?: (
      path: string,
      options?: { recursive?: boolean; regExp?: RegExp }
    ) => WebpackContext;
  }
}

getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
  {
    errorOnUnknownElements: true,
    errorOnUnknownProperties: true,
  }
);

const context = import.meta.webpackContext?.('./', {
  recursive: true,
  regExp: /\.spec\.ts$/,
});

context?.keys().forEach(context);
