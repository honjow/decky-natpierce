import * as React from 'react';

declare global {
  namespace JSX {
    interface ElementChildrenAttribute {
      children: {};
    }

    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
