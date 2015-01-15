#!/usr/bin/env python
# -*- coding: utf8 -*-

import unittest
import json
from datetime import datetime, timedelta
from urlparse import urlparse

from sqlalchemy.exc import IntegrityError

from app import app, db, Organization, Project, Event, Story, Issue, Label
from factories import OrganizationFactory, ProjectFactory, EventFactory, StoryFactory, IssueFactory, LabelFactory


class ApiTest(unittest.TestCase):

    def setUp(self):
        # Set up the database settings
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres@localhost/civic_json_worker_test'
        db.create_all()
        self.app = app.test_client()

    def tearDown(self):
        db.session.close()
        db.drop_all()

    # Test API -----------------------
    def test_current_projects(self):
        '''
        Show three most recently updated github projects
        '''
        organization = OrganizationFactory(name=u'Code for San Francisco')
        db.session.flush()

        ProjectFactory(organization_name=organization.name, name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(organization_name=organization.name, name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco')
        response = json.loads(response.data)

        self.assertEqual(len(response['current_projects']), 3)
        self.assertEqual(response['current_projects'][0]['name'], u'Project 3')
        self.assertEqual(response['current_projects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['current_projects'][2]['name'], u'Project 2')

    def test_all_projects_order(self):
        '''
        Test that projects gets returned in order of last_updated
        '''
        ProjectFactory(name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/projects')
        response = json.loads(response.data)

        self.assertEqual(response['objects'][0]['name'], u'Project 3')
        self.assertEqual(response['objects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['objects'][2]['name'], u'Project 2')
        self.assertEqual(response['objects'][3]['name'], u'Project 1')

    def test_orgs_projects_order(self):
        ''' Test that a orgs projects come back in order of last_updated.
        '''
        organization = OrganizationFactory(name=u'Code for San Francisco')
        db.session.flush()

        ProjectFactory(organization_name=organization.name, name=u'Project 1', last_updated='Mon, 01 Jan 2010 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Project 2', last_updated='Tue, 01 Jan 2011 00:00:00 GMT')
        ProjectFactory(organization_name=organization.name, name=u'Non Github Project', last_updated='Wed, 01 Jan 2013 00:00:00', github_details=None)
        ProjectFactory(organization_name=organization.name, name=u'Project 3', last_updated='Thu, 01 Jan 2014 00:00:00 GMT')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-San-Francisco/projects')
        response = json.loads(response.data)

        self.assertEqual(response['objects'][0]['name'], u'Project 3')
        self.assertEqual(response['objects'][1]['name'], u'Non Github Project')
        self.assertEqual(response['objects'][2]['name'], u'Project 2')
        self.assertEqual(response['objects'][3]['name'], u'Project 1')

    def test_current_events(self):
        '''
        The three soonest upcoming events should be returned.
        If there are no events in the future, no events will be returned
        '''
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'Collective of Ericas')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        EventFactory(organization_name=organization.name, name=u'MLK Day', start_time_notz=datetime.now() + timedelta(25))
        EventFactory(organization_name=organization.name, name=u'Cesar Chavez Day', start_time_notz=datetime.now() + timedelta(37))
        db.session.commit()

        response = self.app.get('/api/organizations/Collective%20of%20Ericas')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['current_events']), 2)
        self.assertEqual(response_json['current_events'][0]['name'], u'New Years')
        self.assertEqual(response_json['current_events'][1]['name'], u'MLK Day')
        self.assertEqual(response_json['current_events'][0]['organization_name'], u'Collective of Ericas')

    def test_all_upcoming_events(self):
        '''
        Test the /events/upcoming_events end point.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        EventFactory(organization_name=organization.name, name=u'Event Four', start_time_notz=datetime.now() + timedelta(100))
        EventFactory(organization_name=organization.name, name=u'Event Seven', start_time_notz=datetime.now() + timedelta(1000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        EventFactory(organization_name=organization.name, name=u'Event Two', start_time_notz=datetime.now() + timedelta(20))
        EventFactory(organization_name=organization.name, name=u'Event Five', start_time_notz=datetime.now() + timedelta(200))
        EventFactory(organization_name=organization.name, name=u'Event Eight', start_time_notz=datetime.now() + timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Event Six', start_time_notz=datetime.now() + timedelta(300))
        EventFactory(organization_name=organization.name, name=u'Event Nine', start_time_notz=datetime.now() + timedelta(3000))
        db.session.commit()

        response = self.app.get('/api/events/upcoming_events')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 9)
        self.assertEqual(response_json['objects'][0]['name'], u'Event One')
        self.assertEqual(response_json['objects'][1]['name'], u'Event Two')
        self.assertEqual(response_json['objects'][8]['name'], u'Event Nine')

    def test_all_upcoming_events_with_params(self):
        '''
        Test the /events/upcoming_events end point with params.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        EventFactory(organization_name=organization.name, name=u'Event Four', start_time_notz=datetime.now() + timedelta(100))
        EventFactory(organization_name=organization.name, name=u'Event Seven', start_time_notz=datetime.now() + timedelta(1000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        EventFactory(organization_name=organization.name, name=u'Event Two', start_time_notz=datetime.now() + timedelta(20))
        EventFactory(organization_name=organization.name, name=u'Event Five', start_time_notz=datetime.now() + timedelta(200))
        EventFactory(organization_name=organization.name, name=u'Event Eight', start_time_notz=datetime.now() + timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Event Six', start_time_notz=datetime.now() + timedelta(300))
        EventFactory(organization_name=organization.name, name=u'Event Nine', start_time_notz=datetime.now() + timedelta(3000))
        db.session.commit()

        response = self.app.get('/api/events/upcoming_events?organization_type=Code for All')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 6)
        self.assertEqual(response_json['objects'][0]['name'], u'Event One')
        self.assertEqual(response_json['objects'][1]['name'], u'Event Three')
        self.assertEqual(response_json['objects'][5]['name'], u'Event Nine')


    def test_all_past_events(self):
        '''
        Test the /events/past_events end point.
        '''
        # World Cup teams
        organization = OrganizationFactory(name=u'USA USA USA', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(1000))
        EventFactory(organization_name=organization.name, name=u'Event One', start_time_notz=datetime.now() + timedelta(10))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'Brazil')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(2000))
        db.session.flush()

        # World Cup teams
        organization = OrganizationFactory(name=u'GER', type=u'Code for All')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Past Event', start_time_notz=datetime.now() - timedelta(3000))
        EventFactory(organization_name=organization.name, name=u'Event Three', start_time_notz=datetime.now() + timedelta(30))
        db.session.commit()

        response = self.app.get('/api/events/past_events?organization_type=Code for All')
        response_json = json.loads(response.data)

        self.assertEqual(len(response_json['objects']), 2)

    def test_current_stories(self):
        '''
        Test that only the two most recent stories are being returned
        '''
        organization = OrganizationFactory(name=u'Collective of Ericas')
        db.session.flush()

        StoryFactory(organization_name=u'Collective of Ericas', title=u'First Story')
        StoryFactory(organization_name=u'Collective of Ericas', title=u'Second Story')
        db.session.commit()

        response = self.app.get('/api/organizations/Collective%20of%20Ericas')
        response_json = json.loads(response.data)
        self.assertEqual(response_json['current_stories'][0]['title'], u'Second Story')
        self.assertEqual(response_json['current_stories'][1]['title'], u'First Story')

    def test_headers(self):
        OrganizationFactory()
        db.session.commit()

        response = self.app.get('/api/organizations')
        assert response.headers['Access-Control-Allow-Origin']  == '*'
        assert response.headers['Content-Type']  == 'application/json'

    def test_404(self):
        response = self.app.get('/blahblahblah')
        assert response.status_code == 404
        response = self.app.get('/api/blahblahblah')
        assert response.status_code == 404
        response = self.app.get('/api/organizations/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/stories/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/events/123456789')
        assert response.status_code == 404
        response = self.app.get('/api/issues/123456789')
        assert response.status_code == 404

    def test_brigade_name_request(self):
        OrganizationFactory(name=u'Code for San Francisco')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for San Francisco')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['city'], unicode)
        assert isinstance(response['current_events'], list)
        assert isinstance(response['latitude'], float)
        assert isinstance(response['longitude'], float)
        assert isinstance(response['name'], unicode)
        assert isinstance(response['current_projects'], list)
        assert isinstance(response['projects_list_url'], unicode)
        assert isinstance(response['rss'], unicode)
        assert isinstance(response['current_stories'], list)
        assert isinstance(response['type'], unicode)
        assert isinstance(response['website'], unicode)

    def test_organizations(self):
        OrganizationFactory()
        db.session.commit()

        response = self.app.get('/api/organizations')
        response = json.loads(response.data)

        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['city'], unicode)
        assert isinstance(response['objects'][0]['current_events'], list)
        assert isinstance(response['objects'][0]['latitude'], float)
        assert isinstance(response['objects'][0]['longitude'], float)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['current_projects'], list)
        assert isinstance(response['objects'][0]['projects_list_url'], unicode)
        assert isinstance(response['objects'][0]['rss'], unicode)
        assert isinstance(response['objects'][0]['current_stories'], list)
        assert isinstance(response['objects'][0]['type'], unicode)
        assert isinstance(response['objects'][0]['website'], unicode)
        assert isinstance(response['objects'][0]['last_updated'], int)
        assert isinstance(response['objects'][0]['started_on'], unicode)

    def test_projects(self):
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/projects')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['categories'], unicode)
        assert isinstance(response['objects'][0]['code_url'], unicode)
        assert isinstance(response['objects'][0]['description'], unicode)
        assert isinstance(response['objects'][0]['github_details'], dict)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['link_url'], unicode)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['type'], unicode)

    def test_pagination(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/projects?per_page=2')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        self.assertEqual(len(response['objects']), 2)
        self.assertEqual(response['pages']['next'], 'http://localhost/api/projects?per_page=2&page=2')
        self.assertEqual(response['pages']['last'], 'http://localhost/api/projects?per_page=2&page=2')
        self.assertNotIn('first', response['pages'])
        self.assertNotIn('prev', response['pages'])

    def test_good_orgs_projects(self):
        organization = OrganizationFactory(name=u'Code for America')
        project = ProjectFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/projects')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_bad_orgs_projects(self):
        ProjectFactory()
        db.session.commit()

        response = self.app.get('/api/organizations/Whatever/projects')
        self.assertEqual(response.status_code, 404)

    def test_stories(self):
        StoryFactory()
        db.session.commit()

        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['link'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['title'], unicode)
        assert isinstance(response['objects'][0]['type'], unicode)

    def test_stories_order(self):
        StoryFactory()
        StoryFactory()
        StoryFactory()
        db.session.commit()

        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        assert (response['objects'][0]['id'] == 3)
        assert (response['objects'][1]['id'] == 2)
        assert (response['objects'][2]['id'] == 1)

    def test_orgs_stories(self):
        organization = OrganizationFactory(name=u'Code for America')
        story = StoryFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_orgs_current_stories_order(self):
        organization = OrganizationFactory(name=u'Code for America')
        StoryFactory(organization_name=u'Code for America')
        StoryFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America')
        response = json.loads(response.data)
        assert response['current_stories'][0]['id'] == 2
        assert response['current_stories'][1]['id'] == 1

    def test_orgs_stories_order(self):
        organization = OrganizationFactory(name=u'Code for America')
        StoryFactory(organization_name=u'Code for America')
        StoryFactory(organization_name=u'Code for America')
        StoryFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        response = json.loads(response.data)
        assert response['objects'][0]['id'] == 3
        assert response['objects'][1]['id'] == 2
        assert response['objects'][2]['id'] == 1

    def test_events(self):
        '''
        Return all events past/future ordered by oldest to newest
        '''
        EventFactory()
        db.session.commit()

        response = self.app.get('/api/events')
        response = json.loads(response.data)
        assert isinstance(response, dict)
        assert isinstance(response['pages'], dict)
        assert isinstance(response['total'], int)
        assert isinstance(response['objects'], list)
        assert isinstance(response['objects'][0]['description'], unicode)
        assert isinstance(response['objects'][0]['end_time'], unicode)
        assert isinstance(response['objects'][0]['event_url'], unicode)
        assert isinstance(response['objects'][0]['api_url'], unicode)
        assert isinstance(response['objects'][0]['id'], int)
        assert isinstance(response['objects'][0]['location'], unicode)
        assert isinstance(response['objects'][0]['name'], unicode)
        assert isinstance(response['objects'][0]['organization'], dict)
        assert isinstance(response['objects'][0]['organization_name'], unicode)
        assert isinstance(response['objects'][0]['start_time'], unicode)

    def test_orgs_events(self):
        organization = OrganizationFactory(name=u'Code for America')
        event = EventFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response, dict)

    def test_utf8_characters(self):
        organization = OrganizationFactory(name=u'Cöde for Ameriça')
        db.session.add(organization)
        db.session.commit()

        response = self.app.get(u'/api/organizations/Cöde for Ameriça')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get(u'/api/organizations/Cöde-for-Ameriça')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get('/api/organizations/C%C3%B6de for Ameri%C3%A7a')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

        response = self.app.get('/api/organizations/C%C3%B6de-for-Ameri%C3%A7a')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        assert isinstance(response['name'], unicode)

    def test_underscores_and_spaces(self):
        organization = OrganizationFactory(name=u'Code for America')
        db.session.add(organization)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        scheme, netloc, path, _, _, _  = urlparse(response['all_events'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)
        scheme, netloc, path, _, _, _  = urlparse(response['all_stories'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)
        scheme, netloc, path, _, _, _  = urlparse(response['all_projects'])
        self.assertTrue('-' in path)
        self.assertFalse('_' in path)
        self.assertFalse(' ' in path)

        response = self.app.get('/api/organizations/Code-for-America')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

        project = ProjectFactory(organization_name=u'Code for America')
        db.session.add(project)
        db.session.commit()

        response = self.app.get('/api/organizations/Code_for_America/projects')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/projects')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        event = EventFactory(organization_name=u'Code for America')
        db.session.add(event)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/events')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/events')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        story = StoryFactory(organization_name=u'Code for America')
        db.session.add(story)
        db.session.commit()

        response = self.app.get('/api/organizations/Code for America/stories')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

        response = self.app.get('/api/organizations/Code_for_America/stories')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['objects'][0]['organization_name'], u'Code for America')

    def test_dashes_in_slugs(self):
        organization = OrganizationFactory(name=u'Code for America')
        event = EventFactory(organization_name=u'Code for America')
        db.session.commit()

        response = self.app.get('/api/organizations/Code-for-America')
        self.assertEqual(response.status_code,200)
        response = json.loads(response.data)
        self.assertEqual(response['name'], u'Code for America')

    def test_org_upcoming_events(self):
        '''
        Only return events occurring in the future
        Make sure that they are ordered from most recent to
        furthest away in the future
        '''
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'International Cat Association')
        db.session.flush()

        # Create multiple events, some in the future, one in the past
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        EventFactory(organization_name=organization.name, name=u'MLK Day', start_time_notz=datetime.now() + timedelta(25))
        db.session.commit()

        # Check that future events are returned in the correct order
        response = self.app.get('/api/organizations/International Cat Association/upcoming_events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'New Years')
        self.assertEqual(response['objects'][1]['name'], u'MLK Day')

    def test_past_events(self):
        '''
        Only return events that occurred in the past
        Make sure they are ordered from most recent to
        furthest in the past
        '''
        # Assuming today is Christmas...
        organization = OrganizationFactory(name=u'International Cat Association')
        db.session.flush()

        # Create multiple events, one in the future, some in the past
        EventFactory(organization_name=organization.name, name=u'Thanksgiving', start_time_notz=datetime.now() - timedelta(30))
        EventFactory(organization_name=organization.name, name=u'Christmas Eve', start_time_notz=datetime.now() - timedelta(1))
        EventFactory(organization_name=organization.name, name=u'New Years', start_time_notz=datetime.now() + timedelta(7))
        db.session.commit()

        # Check that past events are returned in the correct order
        response = self.app.get('/api/organizations/International Cat Association/past_events')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Christmas Eve')
        self.assertEqual(response['objects'][1]['name'], u'Thanksgiving')

    def test_issues(self):
        '''
        Test that issues have everything we expect.
        Make sure linked issues are not included in the linked project
        '''
        organization = OrganizationFactory()
        db.session.add(organization)
        db.session.commit()
        project = ProjectFactory(organization_name=organization.name)
        db.session.add(project)
        db.session.commit()
        issue = IssueFactory(project_id=project.id,title=u'TEST ISSUE',body=u'TEST ISSUE BODY')
        db.session.add(issue)
        db.session.commit()

        response = self.app.get('/api/issues', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)

        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'TEST ISSUE')
        self.assertEqual(response['objects'][0]['body'], u'TEST ISSUE BODY')

        # Check for linked issues in linked project
        self.assertTrue('project' in response['objects'][0])
        self.assertFalse('issues' in response['objects'][0])

        #Check that project_id is hidden
        self.assertTrue('project_id' not in response['objects'][0])

        # Check for linked project issues on single issue
        response = self.app.get('/api/issues/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertTrue('project' in response)
        self.assertTrue('issues' not in response['project'])

    def test_issues_with_labels(self):
        '''
        Test that /api/issues/labels works as expected.
        Should return issues with any of the passed in label names
        '''
        project = ProjectFactory()
        db.session.flush()

        issue = IssueFactory(project_id=project.id)
        issue2 = IssueFactory(project_id=project.id)

        label1 = LabelFactory(name=u'enhancement')
        label2 = LabelFactory(name=u'hack')
        issue.labels = [label1]
        issue2.labels = [label2]

        db.session.commit()

        response = self.app.get('/api/issues/labels/enhancement')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['labels'][0]['name'], u'enhancement')

        response = self.app.get('/api/issues/labels/enhancement,hack')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

    def test_organization_query_filter(self):
        '''
        Test that organization query params work as expected.
        '''
        OrganizationFactory(name=u'Brigade Organization', type=u'Brigade')
        OrganizationFactory(name=u'Bayamon Organization', type=u'Brigade', city=u'Bayamon, PR')
        OrganizationFactory(name=u'Meetup Organization', type=u'Meetup')

        db.session.commit()

        response = self.app.get('/api/organizations?type=Brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Brigade Organization')
        self.assertEqual(response['objects'][1]['name'], u'Bayamon Organization')

        response = self.app.get('/api/organizations?type=Brigade&city=Bayamon,%20PR')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Bayamon Organization')

        response = self.app.get('/api/organizations?type=SomeType')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

    def test_project_query_filter(self):
        '''
        Test that project query params work as expected.
        '''
        brigade = OrganizationFactory(name=u'Whatever', type=u'Brigade')
        brigade_somewhere_far = OrganizationFactory(name=u'Brigade Organization', type=u'Brigade, Code for All')
        web_project = ProjectFactory(name=u'Random Web App', type=u'web service')
        other_web_project = ProjectFactory(name=u'Random Web App 2', type=u'web service', description=u'Another')
        non_web_project = ProjectFactory(name=u'Random Other App', type=u'other service')

        web_project.organization = brigade
        non_web_project.organization =  brigade_somewhere_far

        db.session.add(web_project)
        db.session.add(non_web_project)
        db.session.commit()

        response = self.app.get('/api/projects?type=web%20service')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)
        self.assertEqual(response['objects'][0]['name'], u'Random Web App')
        self.assertEqual(response['objects'][1]['name'], u'Random Web App 2')

        response = self.app.get('/api/projects?type=web%20service&description=Another')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Random Web App 2')

        response = self.app.get('/api/projects?type=different%20service')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 0)

        response = self.app.get('/api/projects?organization_type=Code+for+All')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)

    def test_organization_issues(self):
        '''
        Test getting all of an organization's issues
        '''
        organization = OrganizationFactory(name=u'Civic Project', type=u'Not a brigade')
        db.session.flush()

        project1 = ProjectFactory(organization_name=organization.name, name=u'Civic Project 1')
        project2 = ProjectFactory(organization_name=organization.name, name=u'Civic Project 2')
        db.session.flush()

        issue11 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.1')
        issue12 = IssueFactory(project_id=project1.id, title=u'Civic Issue 1.2')
        issue21 = IssueFactory(project_id=project2.id, title=u'Civic Issue 2.1')
        db.session.commit()

        response = self.app.get('/api/organizations/%s/issues' % organization.name)
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 3)

        self.assertEqual(response['objects'][0]['title'], u'Civic Issue 1.1')

    def test_cascading_delete(self):
        '''
        Test that when an organization is deleted, all of its projects, issues, stories, events are deleted
        '''
        # Create an organization
        organization = OrganizationFactory()
        db.session.flush()

        # Create a project, an event and a story
        project = ProjectFactory(organization_name=organization.name)
        EventFactory(organization_name=organization.name)
        StoryFactory(organization_name=organization.name)
        db.session.flush()

        # Create an issue and give it a label
        issue = IssueFactory(project_id=project.id)
        db.session.flush()

        label = LabelFactory()
        issue.labels = [label]
        db.session.flush()

        # Get all of the stuff
        orgs = Organization.query.all()
        eve = Event.query.all()
        sto = Story.query.all()
        proj = Project.query.all()
        iss = Issue.query.all()
        lab = Label.query.all()

        # Verify they are there
        self.assertEqual(len(orgs), 1)
        self.assertEqual(len(eve), 1)
        self.assertEqual(len(sto), 1)
        self.assertEqual(len(proj), 1)
        self.assertEqual(len(iss), 1)
        self.assertEqual(len(lab), 1)

        # Delete the one organization
        db.session.delete(orgs[0])
        db.session.commit()

        # Get all the stuff again
        orgs = Organization.query.all()
        eve = Event.query.all()
        sto = Story.query.all()
        proj = Project.query.all()
        iss = Issue.query.all()
        lab = Label.query.all()

        # Make sure they are all gone
        self.assertEqual(len(orgs), 0)
        self.assertEqual(len(eve), 0)
        self.assertEqual(len(sto), 0)
        self.assertEqual(len(proj), 0)
        self.assertEqual(len(iss), 0)
        self.assertEqual(len(lab), 0)

    def test_story_query_filter(self):
        org = OrganizationFactory(type=u'Brigade')
        another_org = OrganizationFactory(type=u'Code for All')

        awesome_story = StoryFactory(title=u'Awesome story')
        sad_story = StoryFactory(title=u'Sad story', type=u'a video')

        awesome_story.organization = org
        sad_story.organization = another_org

        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/stories')
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by title should return only 1
        response = self.app.get('/api/stories?title=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome story')

        # Filter by type should return only 1
        response = self.app.get('/api/stories?type=video')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad story')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/stories?organization_type=brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome story')


    def test_events_query_filter(self):
        org = OrganizationFactory(type=u'Brigade')
        another_org = OrganizationFactory(type=u'Code for All')
        awesome_event = EventFactory(name=u'Awesome event')
        sad_event = EventFactory(name=u'Sad event', description=u'sad stuff will happen')

        awesome_event.organization = org
        sad_event.organization = another_org

        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/events')
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by name should return only 1
        response = self.app.get('/api/events?name=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Awesome event')

        # Filter by description should return only 1
        response = self.app.get('/api/events?description=sad%20stuff')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Sad event')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/events?organization_type=brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['name'], u'Awesome event')


    def test_issues_query_filter(self):
        org1 = OrganizationFactory(name=u'Code for Africa', type=u'Code for All')
        org2 = OrganizationFactory(name=u'Code for San Francisco', type=u'Brigade')
        proj = ProjectFactory(type=u'web', organization_name=u'Code for Africa')
        another_proj = ProjectFactory(type=u'mobile', organization_name=u'Code for San Francisco')
        db.session.flush()
        awesome_issue = IssueFactory(title=u'Awesome issue', project_id=proj.id)
        sad_issue = IssueFactory(title=u'Sad issue', body=u'learning swift is sad', project_id=another_proj.id)
        db.session.commit()

        # Make sure total number of stories is 2
        response = self.app.get('/api/issues')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 2)

        # Filter by title should return only 1
        response = self.app.get('/api/issues?title=awesome')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by type should return only 1
        response = self.app.get('/api/issues?body=swift')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad issue')

        # Filter by deep searching project type should return 1
        response = self.app.get('/api/issues?project_type=web')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/issues?organization_type=Code for All')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Awesome issue')

        # Filter by deep searching organization type should return 1
        response = self.app.get('/api/issues?organization_type=Brigade')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['objects'][0]['title'], u'Sad issue')

    def test_org_dont_show_issues(self):
        ''' Test that calls to /organizations dont return project issues '''
        from factories import OrganizationFactory, ProjectFactory, IssueFactory
        organization = OrganizationFactory()
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name)
        db.session.flush()

        issue = IssueFactory(project_id=project.id)
        db.session.commit()

        response = self.app.get('/api/organizations')
        response = json.loads(response.data)
        for org in response['objects']:
            if org['current_projects']:
                self.assertFalse('issues' in org['current_projects'][0])
                break

    def test_issue_cascading_deletes(self):
        ''' Test that labels get deleted when their parent
            issue, project, and org is deleted
        '''

        # set up test objects and delete an issue
        organization = OrganizationFactory(name=u'TEST ORG')
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM issue')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

        # delete a project
        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM project')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

        # delete an organization
        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        db.session.flush()

        label = LabelFactory(issue_id=issue.id)
        db.session.flush()

        db.session.execute('DELETE FROM organization')
        db.session.commit()
        labels = db.session.query(Label).all()
        self.assertFalse(len(labels))

    def test_project_cascading_deletes(self):
        ''' Test that issues get deleted when their parent
            project and org is deleted
        '''

        # set up test objects and delete a project
        organization = OrganizationFactory(name=u'TEST ORG')
        db.session.flush()

        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        another_issue = IssueFactory(title=u'ANOTHER TEST ISSUE', project_id=project.id)
        a_third_issue = IssueFactory(title=u'A THIRD TEST ISSUE', project_id=project.id)
        db.session.commit()

        # make sure the issues are in the db
        issues = db.session.query(Issue).all()
        self.assertTrue(len(issues) == 3)

        db.session.execute('DELETE FROM project')
        db.session.commit()
        issues = db.session.query(Issue).all()
        self.assertFalse(len(issues))

        # delete an organization
        project = ProjectFactory(organization_name=organization.name, name=u'TEST PROJECT')
        db.session.flush()

        issue = IssueFactory(title=u'TEST ISSUE', project_id=project.id)
        another_issue = IssueFactory(title=u'ANOTHER TEST ISSUE', project_id=project.id)
        a_third_issue = IssueFactory(title=u'A THIRD TEST ISSUE', project_id=project.id)
        db.session.commit()

        # make sure the issues are in the db
        issues = db.session.query(Issue).all()
        self.assertTrue(len(issues) == 3)

        db.session.execute('DELETE FROM organization')
        db.session.commit()
        issues = db.session.query(Issue).all()
        self.assertFalse(len(issues))

    def test_create_child_without_parent(self):
        ''' Test that children created without parents cannot be committed to the database
        '''
        test_passed = False
        project = ProjectFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        story = StoryFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        event = EventFactory(organization_name=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        issue = IssueFactory(project_id=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        label = LabelFactory(issue_id=None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)


    def test_set_childs_parent_association_null(self):
        ''' Test that a child's parent association cannot be deleted
        '''

        test_passed = False
        project = ProjectFactory()
        db.session.commit()
        setattr(project, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        story = StoryFactory()
        db.session.commit()
        setattr(story, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        event = EventFactory()
        db.session.commit()
        setattr(event, 'organization_name', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        project = ProjectFactory()
        db.session.flush()
        issue = IssueFactory(project_id=project.id)
        db.session.commit()
        setattr(issue, 'project_id', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)
        db.session.rollback()

        test_passed = False
        project = ProjectFactory()
        db.session.flush()
        issue = IssueFactory(project_id=project.id)
        db.session.flush()
        label = LabelFactory(issue_id=issue.id)
        db.session.commit()
        setattr(label, 'issue_id', None)
        try:
            db.session.commit()
        except IntegrityError:
            test_passed = True

        self.assertTrue(test_passed)


if __name__ == '__main__':
    unittest.main()
