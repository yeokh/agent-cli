#!/usr/bin/env python3
"""
Fetch Red Hat product lifecycle data using Playwright
"""
from playwright.sync_api import sync_playwright
import json
import time

def fetch_rhel_lifecycle():
    """Fetch RHEL lifecycle information"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://access.redhat.com/product-life-cycles/?product=Red%20Hat%20Enterprise%20Linux", 
                     wait_until="networkidle", timeout=30000)
            time.sleep(2)
            content = page.inner_text("body")
            browser.close()
            return content
        except Exception as e:
            browser.close()
            return f"Error fetching RHEL lifecycle: {str(e)}"

def fetch_openshift_lifecycle():
    """Fetch OpenShift lifecycle information"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://access.redhat.com/support/policy/updates/openshift", 
                     wait_until="networkidle", timeout=30000)
            time.sleep(2)
            content = page.inner_text("body")
            browser.close()
            return content
        except Exception as e:
            browser.close()
            return f"Error fetching OpenShift lifecycle: {str(e)}"

def fetch_ansible_lifecycle():
    """Fetch Ansible Automation Platform lifecycle information"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://access.redhat.com/support/policy/updates/ansible-automation-platform", 
                     wait_until="networkidle", timeout=30000)
            time.sleep(2)
            content = page.inner_text("body")
            browser.close()
            return content
        except Exception as e:
            browser.close()
            return f"Error fetching Ansible lifecycle: {str(e)}"

def fetch_satellite_lifecycle():
    """Fetch Satellite lifecycle information"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("https://access.redhat.com/support/policy/updates/satellite", 
                     wait_until="networkidle", timeout=30000)
            time.sleep(2)
            content = page.inner_text("body")
            browser.close()
            return content
        except Exception as e:
            browser.close()
            return f"Error fetching Satellite lifecycle: {str(e)}"

if __name__ == "__main__":
    print("Fetching RHEL lifecycle data...")
    rhel_data = fetch_rhel_lifecycle()
    print("\n=== RHEL LIFECYCLE DATA ===")
    print(rhel_data[:2000])
    print("\n\nFetching OpenShift lifecycle data...")
    ocp_data = fetch_openshift_lifecycle()
    print("\n=== OPENSHIFT LIFECYCLE DATA ===")
    print(ocp_data[:2000])
    print("\n\nFetching Ansible Automation Platform lifecycle data...")
    ansible_data = fetch_ansible_lifecycle()
    print("\n=== ANSIBLE AUTOMATION PLATFORM LIFECYCLE DATA ===")
    print(ansible_data[:2000])
    print("\n\nFetching Satellite lifecycle data...")
    sat_data = fetch_satellite_lifecycle()
    print("\n=== SATELLITE LIFECYCLE DATA ===")
    print(sat_data[:2000])
