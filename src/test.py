import unittest
import os
import stat
import time
import random
from git import *

class TestGitFuse(unittest.TestCase):
	path = None
	repoPath = None
	repo = None

	def setUp(self):
		self.repoPath = os.getenv('GITPYTHON_TEST_REPO_DIR').rstrip('/') + '/';
		self.path = os.getenv('GITPYTHON_TEST_DIR').rstrip('/') + '/';
		self.repo = Repo(self.repoPath)

        def test_change_file_permissions(self):
		testtext = 'This is a sample text to write on the file'

                fp = open(self.path + 'permissions', 'w')
		fp.write(testtext)
                fp.close()
		os.chmod(self.path + 'permissions', 0755)
		statinfo = os.stat(self.path + 'permissions')
		self.assertTrue(statinfo.st_mode & 0755 == 0755) # There are other flags besides permissions
		self.assertEqual(statinfo.st_mode & stat.S_IFDIR, 0)
		self.assertEqual(statinfo.st_mode & stat.S_IFREG, stat.S_IFREG)
		self.assertEqual(statinfo.st_size, len(testtext))
		self.assertTrue(time.time() - statinfo.st_atime < 2)
		self.assertTrue(time.time() - statinfo.st_mtime < 2)
		self.assertTrue(time.time() - statinfo.st_ctime < 2)

		#NOTE: we are checking local permissions, not git permissions.
		#This is related to git design limitations and cross platform support.

	def test_create_empty_file(self):
		self.assertFalse(os.path.exists(self.repoPath + 'data'))
		fp = open(self.path + 'data', 'w')
		fp.close()
		self.assertTrue(os.path.exists(self.repoPath + 'data'))
		repo = Repo(self.repoPath)
		stats = repo.head.commit.parents[0].stats # HEAD is the file edit - parent is the first commit creating the file
		self.assertEqual(stats.total['files'], 1)

		statinfo = os.stat(self.repoPath + 'data')
		self.assertEqual(statinfo.st_mode & stat.S_IFREG, stat.S_IFREG) # checking if real file was created

	def test_edit_file(self):
		text ='hello\nworld'
		fp = open(self.path + 'data', 'w')
		fp.write(text)
		fp.close()
		stats = self.repo.head.commit.stats
		self.assertEqual(stats.files['data']['insertions'], 2)

		statinfo = os.stat(self.repoPath + 'data')
		self.assertEqual(statinfo.st_size, len(text)) # checking if real file was created

	def test_delete_file(self):
		os.unlink(self.path + 'data')
		diffIndex = self.repo.head.commit.parents[0].diff(self.repo.head.commit)
		runDeleted = False
		for diff in diffIndex.iter_change_type('D'):
			runDeleted = True
			self.assertEqual(diff.a_blob.path, 'data')
			self.assertEqual(diff.deleted_file, True)
		self.assertEqual(runDeleted, True)

		self.assertFalse(os.path.exists(self.repoPath + 'data'))

	def test_create_folder(self):
		os.mkdir(self.path + 'dir');
		self.assertTrue(os.path.exists(self.path + 'dir'))
		self.assertTrue(os.path.exists(self.repoPath + 'dir'))
		os.rmdir(self.path + 'dir');
		self.assertFalse(os.path.exists(self.path + 'dir'))
		self.assertFalse(os.path.exists(self.repoPath + 'dir'))

	def test_rename_non_empty_folder(self):
		os.mkdir(self.path + 'dir');
		fp = open(self.path + 'dir/data', 'w')
		fp.close()
		os.rename(self.path + 'dir', self.path + 'dir2');
		self.assertTrue(os.path.exists(self.path + 'dir2'))
		self.assertTrue(os.path.exists(self.repoPath + 'dir2'))
		self.assertTrue(os.path.exists(self.path + 'dir2/data'))
		self.assertTrue(os.path.exists(self.repoPath + 'dir2/data'))
		self.assertFalse(os.path.exists(self.path + 'dir'))
		self.assertFalse(os.path.exists(self.repoPath + 'dir'))
		os.unlink(self.path + 'dir2/data')
		os.rmdir(self.path + 'dir2');

	def test_rename_empty_folder(self):
		os.mkdir(self.path + 'dir');
		os.rename(self.path + 'dir', self.path + 'dir2');
		self.assertTrue(os.path.exists(self.path + 'dir2'))
		self.assertTrue(os.path.exists(self.repoPath + 'dir2'))
		self.assertFalse(os.path.exists(self.path + 'dir'))
		self.assertFalse(os.path.exists(self.repoPath + 'dir'))
		os.rmdir(self.path + 'dir2');

	def test_hook_repo_symlink(self):
		self.assertEqual(os.readlink(self.path + '.gitfuserepo'), self.repoPath)

	def test_hook_history_exists(self):
		self.assertTrue(os.path.exists(self.path + '.githistory'))

	def test_hook_history_create_commits(self):
		filename = 'history'
		self.assertFalse(os.path.exists(self.repoPath + filename))
		fp = open(self.path + filename, 'w')
		fp.close()
		self.assertTrue(os.path.exists(self.repoPath + filename))
		number_of_commits = 0
		for commit in os.listdir(self.path + '.githistory/' + filename):
			number_of_commits+=1
		self.assertEqual(number_of_commits, 1)
		fp = open(self.path + filename, 'w')
		fp.write('asd')
		fp.close()
		number_of_commits = 0
		for commit in os.listdir(self.path + '.githistory/' + filename):
			number_of_commits+=1
		self.assertEqual(number_of_commits, 2)

	def test_hook_history_create_commits_on_subfolders(self):
		foldername = 'testdir'
		os.mkdir(self.path + foldername)
		filename = foldername + '/history'
		self.assertFalse(os.path.exists(self.repoPath + filename))
		fp = open(self.path + filename, 'w')
		fp.close()
		self.assertTrue(os.path.exists(self.repoPath + filename))
		number_of_commits = 0
		for commit in os.listdir(self.path + '.githistory/' + filename):
			number_of_commits+=1
		self.assertEqual(number_of_commits, 1)
		fp = open(self.path + filename, 'w')
		fp.write('asd')
		fp.close()
		number_of_commits = 0
		for commit in os.listdir(self.path + '.githistory/' + filename):
			number_of_commits+=1
		self.assertEqual(number_of_commits, 2)

	def test_hook_history_read_commits(self):
		filename = 'history2'
		self.assertFalse(os.path.exists(self.repoPath + filename))
		fp = open(self.path + filename, 'w')
		fp.close()
		self.assertTrue(os.path.exists(self.repoPath + filename))
		commits = []
		for commit in os.listdir(self.path + '.githistory/' + filename):
			commits.append(commit)

		content = 'asd'
		fp = open(self.path + filename, 'w')
		fp.write(content)
		fp.close()

		new_commit = None
		for commit in os.listdir(self.path + '.githistory/' + filename):
			if commits.count(commit) == 0:
				new_commit = commit
				break

		self.assertNotEqual(new_commit, None)

		with open(self.path + '.githistory/' + filename + '/' + new_commit, 'r') as f:
			read_data = f.read()
		self.assertEqual(read_data, content)

	def test_hook_history_read_commits_more_than_65536(self):
		filename = 'history3'
		self.assertFalse(os.path.exists(self.repoPath + filename))
		fp = open(self.path + filename, 'w')
		fp.close()
		self.assertTrue(os.path.exists(self.repoPath + filename))
		commits = []
		for commit in os.listdir(self.path + '.githistory/' + filename):
			commits.append(commit)

		content = ''
		while len(content) < 65536:
			content += get_random_word(random.randint(5, 15)) + ' '

		fp = open(self.path + filename, 'w')
		fp.write(content)
		fp.close()

		new_commit = None
		for commit in os.listdir(self.path + '.githistory/' + filename):
			if commits.count(commit) == 0:
				new_commit = commit
				break

		self.assertNotEqual(new_commit, None)

		with open(self.path + '.githistory/' + filename + '/' + new_commit, 'r') as f:
			read_data = f.read()
		self.assertEqual(read_data, content)

def get_random_word(wordLen):
    word = ''
    for i in range(wordLen):
        word += random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
    return word

if __name__ == '__main__':
	suite = unittest.TestLoader().loadTestsFromTestCase(TestGitFuse)
	unittest.TextTestRunner(verbosity=2).run(suite)
